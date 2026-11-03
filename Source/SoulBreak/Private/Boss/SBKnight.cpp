#include "Boss/SBKnight.h"
#include "AI/SBBossController.h"
#include "Combat/SBImpact.h"
#include "Player/SBHero.h"
#include "Components/CapsuleComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Navigation/PathFollowingComponent.h"

ASBKnight::ASBKnight()
{
    Health=400;
    GetCapsuleComponent()->InitCapsuleSize(44,128);
    GetCharacterMovement()->MaxWalkSpeed=235;
    GetCharacterMovement()->bUseRVOAvoidance=false;
    AutoPossessAI=EAutoPossessAI::PlacedInWorldOrSpawned;
    AIControllerClass=ASBBossController::StaticClass();
    Body=CreateDefaultSubobject<UCapsuleComponent>(TEXT("TorsoTarget"));
    Body->SetupAttachment(RootComponent); Body->InitCapsuleSize(37,72);
    Arm=CreateDefaultSubobject<UCapsuleComponent>(TEXT("RightArmTarget"));
    Arm->SetupAttachment(RootComponent); Arm->InitCapsuleSize(25,39);
    for (auto* Part : {Body.Get(),Arm.Get()})
    {
        Part->SetCollisionEnabled(ECollisionEnabled::QueryOnly); Part->SetCollisionResponseToAllChannels(ECR_Ignore);
        Part->SetCollisionObjectType(ECC_WorldDynamic); Part->SetGenerateOverlapEvents(false); Part->SetCanEverAffectNavigation(false);
    }
    Telegraph=CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("StompWarning"));
    Telegraph->SetupAttachment(RootComponent); Telegraph->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Telegraph->SetCanEverAffectNavigation(false); Telegraph->SetCastShadow(false); Telegraph->SetVisibility(false);
}
void ASBKnight::BeginPlay()
{
    Super::BeginPlay();
    LoadFighter(TEXT("Knight"),275.f);
    FallenBlade=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/SoulBreak/Characters/SM_FallenBlade.SM_FallenBlade"),nullptr,LOAD_NoWarn);
    Body->SetRelativeLocation(FVector(0,0,12));
    // Anchor the capsule halfway between gauntlet and pauldron. Keep its shape in world centimetres
    // regardless of the author's armature units and its bone's local axes.
    Arm->SetRelativeLocation(FVector(0,48,44));
    Telegraph->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));
    RingMat=UMaterialInstanceDynamic::Create(LoadObject<UMaterialInterface>(nullptr,TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial")),this);
    if (RingMat) { RingMat->SetVectorParameterValue(TEXT("Color"),FLinearColor(1.9,.24,.025)); Telegraph->SetMaterial(0,RingMat); }
    for (int32 I=0;I<72;++I) Telegraph->AddInstance(FTransform::Identity);
}
void ASBKnight::StartEncounter(ASBHero* Target)
{
    if (!Target || Health<=0 || bEncounterActive) return;
    bEncounterActive=true; Hero=Target; Hero->SetKnight(this);
    if (!GetController()) SpawnDefaultController();
    Enter(ESBKnightAction::Chase,0.f);
    if (auto* AI=Cast<ASBBossController>(Controller)) AI->BeginDuel(*this);
}
void ASBKnight::StopMoving()
{
    if (auto* AI=Cast<AAIController>(Controller)) AI->StopMovement();
    GetCharacterMovement()->StopMovementImmediately();
}
void ASBKnight::StopEncounter()
{
    if (!bEncounterActive) return;
    bEncounterActive=false; ++AttackGeneration; StopMoving();
    if (Action!=ESBKnightAction::Dead) {Enter(ESBKnightAction::Idle,0);Pose(TEXT("Idle"),true);}
    Telegraph->SetVisibility(false);
}
const FSBPattern* ASBKnight::CurrentPattern() const
{
    if (!CombatData) return nullptr;
    switch(Action)
    {
    case ESBKnightAction::SwordSweep: return &CombatData->Sweep;
    case ESBKnightAction::Bash: return &CombatData->Bash;
    case ESBKnightAction::Stomp: return &CombatData->Stomp;
    default: return nullptr;
    }
}
void ASBKnight::Enter(ESBKnightAction State,float Duration)
{
    Action=State; PatternElapsed=0; TelegraphDuration=0; StateDuration=Duration; bImpactResolved=false;
    ++AttackGeneration; Telegraph->SetVisibility(false);
    switch(State)
    {
    case ESBKnightAction::SwordSweep: PatternLabel=TEXT("검 가로베기");break;
    case ESBKnightAction::Bash: PatternLabel=TEXT("방패 밀치기");break;
    case ESBKnightAction::Stomp: PatternLabel=TEXT("발구르기");break;
    case ESBKnightAction::Stagger: PatternLabel=TEXT("경직");break;
    case ESBKnightAction::Transition: PatternLabel=bArmBroken ? TEXT("오른팔 파괴"):TEXT("깨어난 맹세");break;
    case ESBKnightAction::Chase: PatternLabel=TEXT("추적");break;
    case ESBKnightAction::Dead: PatternLabel=TEXT("격파");break;
    default: PatternLabel.Empty();
    }
    if (auto* AI=Cast<ASBBossController>(Controller)) AI->Sync(*this);
}
void ASBKnight::StartPattern(ESBKnightAction Pattern)
{
    StopMoving(); Face(Hero->GetActorLocation()-GetActorLocation(),180);
    Enter(Pattern,0);
    ++PatternsStarted; bPreferStomp=false;
    const FSBPattern* P=CurrentPattern(); check(P);
    StateDuration=P->Duration(); TelegraphDuration=P->Windup;
    FName Clip;
    if (Pattern==ESBKnightAction::Stomp)
    {
        NextStompTime=GetWorld()->TimeSeconds+CombatData->StompCooldown;
        Telegraph->SetVisibility(true); UpdateStompRing(0); Clip=TEXT("Stomp");
    }
    else Clip=Pattern==ESBKnightAction::SwordSweep ? TEXT("SwordSweep"):TEXT("Bash");
    Pose(Clip,false,StateDuration,true);
    PlayCue(TEXT("Shield"),.44f,Pattern==ESBKnightAction::Stomp ? .63f:.84f);
    UE_LOG(LogTemp,Display,TEXT("SoulBreak pattern=%s phase=%d arm=%d generation=%d"),*PatternLabel,Phase,!bArmBroken,AttackGeneration);
}
void ASBKnight::SelectOrChase(float Dt)
{
    const FVector To=Hero->GetActorLocation()-GetActorLocation();
    const float D=To.Size2D();
    const bool CanStomp=Phase==2 && D<=CombatData->Stomp.Range && GetWorld()->TimeSeconds>=NextStompTime;
    if (CanStomp && bPreferStomp) {NextPattern=0;StartPattern(ESBKnightAction::Stomp); return;}
    const ESBKnightAction Options[]={ESBKnightAction::SwordSweep,ESBKnightAction::Bash,ESBKnightAction::Stomp};
    const bool Valid[]={!bArmBroken && D<=CombatData->Sweep.Range,D<=CombatData->Bash.Range,CanStomp};
    for (int32 I=0;I<3;++I)
    {
        int32 Index=(NextPattern+I)%3;
        if (Valid[Index]) { NextPattern=(Index+1)%3; StartPattern(Options[Index]); return; }
    }
    if (Action!=ESBKnightAction::Chase) Enter(ESBKnightAction::Chase,0);
    auto* AI=Cast<AAIController>(Controller);
    if (AI && GetWorld()->TimeSeconds>=NextPathUpdate)
    {
        NextPathUpdate=GetWorld()->TimeSeconds+.24f; AI->MoveToActor(Hero,60,false,true,true);
    }
    const bool Following=AI && AI->GetMoveStatus()==EPathFollowingStatus::Moving;
    if (!Following) AddMovementInput(To.GetSafeNormal2D(),1.f,true);
    Face(Following && !GetVelocity().IsNearlyZero() ? GetVelocity() : To,Dt*280);
    Locomotion(235);
}
void ASBKnight::Think(float Dt)
{
    if (!bEncounterActive || !Hero || Hero->Health<=0 || Health<=0 || !CombatData) return;
    PatternElapsed+=Dt;
    if (Action==ESBKnightAction::Transition || Action==ESBKnightAction::Stagger)
    {
        if (PatternElapsed>=StateDuration) Enter(ESBKnightAction::Idle,0); return;
    }
    if (const FSBPattern* P=CurrentPattern())
    {
        if (Action==ESBKnightAction::Stomp) UpdateStompRing(FMath::Clamp(PatternElapsed/P->Windup,0.f,1.f));
        // Track the player only during the early tell; closing angle or leaving range can avoid the strike.
        if (PatternElapsed<P->Windup*.6f) Face(Hero->GetActorLocation()-GetActorLocation(),Dt*95.f);
        if (!bImpactResolved && PatternElapsed>=P->Windup)
        {
            const int32 Generation=AttackGeneration;
            bImpactResolved=true;
            const bool Sword=Action==ESBKnightAction::SwordSweep;
            const bool Stomp=Action==ESBKnightAction::Stomp;
            PlayCue(Stomp?TEXT("Stomp"):Sword?TEXT("Swing"):TEXT("Shield"),1.f,Stomp?1.f:.81f);
            if (Stomp && FVector::Dist2D(Hero->GetActorLocation(),GetActorLocation())<520) Hero->ImpactCamera(.6f);
            const FVector To=Hero->GetActorLocation()-GetActorLocation();
            const bool InAngle=Stomp || FVector::DotProduct(To.GetSafeNormal2D(),GetActorForwardVector())>=FMath::Cos(FMath::DegreesToRadians(P->Angle*.5f));
            if (To.Size2D()<=P->Range && InAngle) Hero->ReceivePattern(P->Damage,Sword);
            // A parry or break can transition state synchronously while delivering this hit.
            if (Generation!=AttackGeneration) return;
        }
        if (PatternElapsed>=P->Windup+P->Active) Telegraph->SetVisibility(false);
        if (PatternElapsed>=StateDuration) Enter(ESBKnightAction::Idle,0);
        return;
    }
    SelectOrChase(Dt);
}
void ASBKnight::UpdateStompRing(float Progress)
{
    constexpr int32 Count=36;
    for (int32 J=0;J<2;++J)
    {
        float R=CombatData->Stomp.Range*(J==0 ? 1.f:FMath::Lerp(.16f,.985f,Progress));
        for (int32 I=0;I<Count;++I)
        {
            float A=I*2*PI/Count; FVector P(R*FMath::Cos(A),R*FMath::Sin(A),-GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+4.f);
            FTransform T(FRotator(0,FMath::RadiansToDegrees(A)+90,0),P,FVector((2*PI*R/Count)/100.f*.92f,J==0?.061f:.034f,.018f));
            Telegraph->UpdateInstanceTransform(J*Count+I,T,false,J==1 && I==Count-1,true);
        }
    }
}
void ASBKnight::Tick(float Dt)
{
    Super::Tick(Dt);
    if (Health<=0)
    {
        PatternElapsed+=Dt;
        return;
    }
    if (!bArmBroken && GetMesh()->DoesSocketExist(TEXT("UpperArmR")))
    {
        FVector Shoulder=GetMesh()->GetSocketLocation(TEXT("UpperArmR")),Elbow=GetMesh()->GetSocketLocation(TEXT("ForearmR"));
        Arm->SetWorldLocationAndRotation((Shoulder+Elbow)*.5f,FRotationMatrix::MakeFromZ(Shoulder-Elbow).ToQuat());
    }
    if (bEncounterActive)
    {
        BlackboardClock+=Dt;
        if (BlackboardClock>=.1f)
        {
            BlackboardClock=0;
            if (auto* AI=Cast<ASBBossController>(Controller)) AI->Sync(*this);
        }
    }
}
FVector ASBKnight::ArmPoint() const {return Arm->GetComponentLocation();}
void ASBKnight::TraceSword(const FVector& From,const FVector& To,bool& bBody,bool& bArm) const
{
    if (!bEncounterActive || Health<=0) return;
    FHitResult Hit;
    const FCollisionShape Sphere=FCollisionShape::MakeSphere(12.f);
    if (!bArm && !bArmBroken) bArm=Arm->SweepComponent(Hit,From,To,FQuat::Identity,Sphere);
    if (!bBody) bBody=Body->SweepComponent(Hit,From,To,FQuat::Identity,Sphere);
}
void ASBKnight::OnParried()
{
    if (!bEncounterActive || Action!=ESBKnightAction::SwordSweep || Health<=0) return;
    StopMoving(); Enter(ESBKnightAction::Stagger,1.f);
    Pose(TEXT("Stagger"),false,1,true); HitPulse=1;
    if (Hero && Hero->GetMesh()->DoesSocketExist(TEXT("BladeBase")))
    {
        const FVector Bind=FMath::Lerp(Hero->GetMesh()->GetSocketLocation(TEXT("BladeBase")),
            Hero->GetMesh()->GetSocketLocation(TEXT("BladeTip")),.58);
        if (ASBImpact* Glint=GetWorld()->SpawnActor<ASBImpact>(Bind,Hero->GetActorRotation()))
            Glint->Launch(nullptr,FVector::ZeroVector,Hero->GetActorLocation().Z-Hero->GetCapsuleComponent()->GetScaledCapsuleHalfHeight(),
                1.f,FLinearColor(.52f,1.35f,1.05f),1.45f);
    }
}
void ASBKnight::BreakArm()
{
    ++BreakCount;
    const FVector Hand=GetMesh()->DoesSocketExist(TEXT("HandR")) ? GetMesh()->GetSocketLocation(TEXT("HandR")) : ArmPoint();
    if (auto* Fx=GetWorld()->SpawnActor<ASBImpact>(Hand,GetActorRotation()))
        Fx->Launch(FallenBlade,GetActorRightVector()*125+FVector(0,0,102),GetActorLocation().Z-GetCapsuleComponent()->GetScaledCapsuleHalfHeight(),GetMesh()->GetRelativeScale3D().X,FLinearColor(1,.47,.08));
    Arm->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    GetMesh()->HideBoneByName(TEXT("UpperArmR"),EPhysBodyOp::PBO_None);
    PlayCue(TEXT("Break"),1.15f); if (Hero) Hero->ImpactCamera(1);
}
void ASBKnight::ApplySwordHit(int32 Id,float Damage,bool HitArm)
{
    if (!bEncounterActive) return;
    const int32 OldPhase=Phase;
    ESBHitResult R=SBCombat::Resolve(Id,LastHitId,Damage,HitArm,Health,ArmHealth,bArmBroken,Phase);
    if (R==ESBHitResult::Miss) return;
    HitPulse=1.f;
    PlayCue(TEXT("Impact"),.9f,HitArm?1.10f:.86f);
    if (R==ESBHitResult::Death)
    {
        StopMoving(); Enter(ESBKnightAction::Dead,1.25f); Pose(TEXT("Death"),false,1.25f,true);
        bEncounterActive=false; return;
    }
    if (R==ESBHitResult::Broken) BreakArm();
    if (OldPhase!=Phase) { ++PhaseChanges;bPreferStomp=true; }
    if (R==ESBHitResult::Broken || R==ESBHitResult::Phase)
    {
        StopMoving(); Enter(OldPhase!=Phase ? ESBKnightAction::Transition : ESBKnightAction::Stagger,1.f);
        Pose(R==ESBHitResult::Broken ? TEXT("Sunder") : TEXT("Stagger"),false,1.f,true);
    }
    else if (auto* Fx=GetWorld()->SpawnActor<ASBImpact>(HitArm ? ArmPoint() : GetActorLocation()+GetActorForwardVector()*33.f,GetActorRotation()))
        Fx->Launch(nullptr,FVector::ZeroVector,GetActorLocation().Z-GetCapsuleComponent()->GetScaledCapsuleHalfHeight(),1,HitArm ? FLinearColor(1,.6,.09) : FLinearColor(.25,.85,.95));
    UE_LOG(LogTemp,Display,TEXT("SoulBreak hit=%d hp=%.0f arm=%.0f phase=%d"),Id,Health,ArmHealth,Phase);
}
