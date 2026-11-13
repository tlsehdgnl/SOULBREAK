#include "Boss/SBKnight.h"
#include "AI/SBBossController.h"
#include "Combat/SBImpact.h"
#include "Combat/SBGroundDust.h"
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
    Shield=CreateDefaultSubobject<UCapsuleComponent>(TEXT("ShieldTarget"));
    Shield->SetupAttachment(RootComponent); Shield->InitCapsuleSize(27,43);
    Knee=CreateDefaultSubobject<UCapsuleComponent>(TEXT("LeftKneeTarget"));
    Knee->SetupAttachment(RootComponent); Knee->InitCapsuleSize(20,24);
    for (auto* Part : {Body.Get(),Arm.Get(),Shield.Get(),Knee.Get()})
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
    Shield->SetRelativeLocation(FVector(22,-45,12));
    Knee->SetRelativeLocation(FVector(12,-19,-57));
    ShieldHealth=CombatData->ShieldDurability;
    KneeHealth=CombatData->KneeDurability;
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
    StopMoving();
    Face(Target->GetActorLocation()-GetActorLocation(),180.f);
    Enter(ESBKnightAction::Challenge,.90f);
    // Finish on the raised guard, before the sweep's first attacking pose.
    Pose(TEXT("SwordSweep"),false,StateDuration/.38f,true);
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
    case ESBKnightAction::ShieldCharge: return &CombatData->ShieldCharge;
    case ESBKnightAction::BellWave: return &CombatData->BellWave;
    case ESBKnightAction::ShoulderCheck: return &CombatData->ShoulderCheck;
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
    case ESBKnightAction::ShieldCharge: PatternLabel=TEXT("방패 돌진");break;
    case ESBKnightAction::BellWave: PatternLabel=TEXT("진혼의 파동");break;
    case ESBKnightAction::ShoulderCheck: PatternLabel=TEXT("어깨 받기");break;
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
    StateDuration=P->Windup+P->Active+SBCombat::RecoveryDuration(Pattern,P->Recovery);
    TelegraphDuration=P->Windup;
    FName Clip=TEXT("Bash");
    FName Cue=TEXT("Shield");
    switch (Pattern)
    {
    case ESBKnightAction::Stomp:
        NextStompTime=GetWorld()->TimeSeconds+CombatData->StompCooldown;
        Telegraph->SetVisibility(true); UpdateRing(P->Range,P->Range*.16f); Clip=TEXT("Stomp");
        break;
    case ESBKnightAction::ShieldCharge:
        ChargeForward=GetActorForwardVector();
        ChargeDistance=FMath::Clamp(float(FVector::Dist2D(Hero->GetActorLocation(),GetActorLocation())+95.),250.f,P->Range);
        bChargeBlocked=false; bChargeConnected=false;
        NextChargeTime=GetWorld()->TimeSeconds+5.25f;
        Telegraph->SetVisibility(true); UpdateChargeLane(); Clip=TEXT("ShieldCharge");Cue=TEXT("Charge");
        break;
    case ESBKnightAction::BellWave:
        NextWaveTime=GetWorld()->TimeSeconds+5.6;
        PreviousWaveDistance=FVector::Dist2D(Hero->GetActorLocation(),GetActorLocation());
        Telegraph->SetVisibility(true); UpdateRing(112.f,100.f); Clip=TEXT("BellWave");Cue=TEXT("Wave");
        break;
    case ESBKnightAction::ShoulderCheck: Clip=TEXT("ShoulderCheck");break;
    case ESBKnightAction::SwordSweep: Clip=TEXT("SwordSweep");break;
    default: break;
    }
    Pose(Clip,false,StateDuration,true);
    PlayCue(Cue,Cue==TEXT("Shield") ? .44f:.8f,Pattern==ESBKnightAction::Stomp ? .63f:1.f);
    UE_LOG(LogTemp,Display,TEXT("SoulBreak pattern=%s phase=%d arm=%d generation=%d"),*PatternLabel,Phase,!bArmBroken,AttackGeneration);
}
void ASBKnight::SelectOrChase(float Dt)
{
    const FVector To=Hero->GetActorLocation()-GetActorLocation();
    const float D=To.Size2D();
    const double Now=GetWorld()->TimeSeconds;
    const bool CanStomp=Phase==2 && !bKneeBroken && D<=CombatData->Stomp.Range && Now>=NextStompTime;
    if (CanStomp && bPreferStomp) {NextPattern=0;StartPattern(ESBKnightAction::Stomp); return;}
    const ESBKnightAction Options[]={ESBKnightAction::SwordSweep,ESBKnightAction::Bash,ESBKnightAction::Stomp,
        ESBKnightAction::ShieldCharge,ESBKnightAction::BellWave,ESBKnightAction::ShoulderCheck};
    const bool Valid[]={!bArmBroken && D<=CombatData->Sweep.Range,!bShieldBroken && D<=CombatData->Bash.Range,CanStomp,
        !bShieldBroken && D>=245.f && D<=CombatData->ShieldCharge.Range && Now>=NextChargeTime,
        Phase==2 && D<=CombatData->BellWave.Range && Now>=NextWaveTime,
        bShieldBroken && D<=CombatData->ShoulderCheck.Range};
    constexpr int32 Count=UE_ARRAY_COUNT(Options);
    for (int32 I=0;I<Count;++I)
    {
        int32 Index=(NextPattern+I)%Count;
        if (Valid[Index]) { NextPattern=(Index+1)%Count; StartPattern(Options[Index]); return; }
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
    const float Previous=PatternElapsed;
    PatternElapsed+=Dt;
    if (Action==ESBKnightAction::Challenge || Action==ESBKnightAction::ShieldRecoil)
    {
        if (Action==ESBKnightAction::Challenge && Previous<.40f && PatternElapsed>=.40f)
            PlayCue(TEXT("HeavyStep"),.95f,.88f);
        if (Action==ESBKnightAction::ShieldRecoil && Previous<.26f && PatternElapsed>=.26f)
        {
            // Recover from the arm flinch into the shoulder-first stance before the shove.
            Pose(TEXT("ShoulderCheck"),false,(StateDuration-.26f)/.32f,true);
        }
        if (PatternElapsed>=StateDuration) SelectOrChase(Dt);
        return;
    }
    if (Action==ESBKnightAction::Transition || Action==ESBKnightAction::Stagger)
    {
        if (PatternElapsed>=StateDuration) Enter(ESBKnightAction::Idle,0); return;
    }
    if (const FSBPattern* P=CurrentPattern())
    {
        // Contact landmarks from Tools/Art/choreography.py; data edits retain the same visual impact.
        float Contact=.454f, FollowThrough=.62f;
        switch (Action)
        {
        case ESBKnightAction::Bash: Contact=.45f; FollowThrough=.56f; break;
        case ESBKnightAction::Stomp: Contact=.46f; FollowThrough=.64f; break;
        case ESBKnightAction::ShieldCharge: Contact=.365f; FollowThrough=.519f; break;
        case ESBKnightAction::BellWave: Contact=.47f; FollowThrough=.72f; break;
        case ESBKnightAction::ShoulderCheck: Contact=.415f; FollowThrough=.60f; break;
        default: break;
        }
        SyncAttackPose(PatternElapsed,P->Windup,P->Windup+P->Active,StateDuration,Contact,FollowThrough);
        const int32 Generation=AttackGeneration;
        if (Action==ESBKnightAction::ShieldCharge) TickCharge(*P,Previous);
        else if (Action==ESBKnightAction::BellWave) TickWave(*P,Previous);
        else
        {
            if (Action==ESBKnightAction::Stomp && Telegraph->IsVisible())
                UpdateRing(P->Range,P->Range*FMath::Lerp(.16f,.985f,FMath::Clamp(PatternElapsed/P->Windup,0.f,1.f)));
            // Track the player only during the early tell; closing angle or leaving range can avoid the strike.
            if (PatternElapsed<P->Windup*.6f) Face(Hero->GetActorLocation()-GetActorLocation(),Dt*95.f);
            if (!bImpactResolved && PatternElapsed>=P->Windup)
            {
                bImpactResolved=true;
                const bool Sword=Action==ESBKnightAction::SwordSweep;
                const bool Stomp=Action==ESBKnightAction::Stomp;
                PlayCue(Stomp?TEXT("Stomp"):Sword?TEXT("Swing"):TEXT("Shield"),1.f,Stomp?1.f:.81f);
                if (Stomp) ASBGroundDust::Kick(GetWorld(),GetCharacterMovement()->GetActorFeetLocation(),FVector::ZeroVector,210.f);
                if (Stomp && FVector::Dist2D(Hero->GetActorLocation(),GetActorLocation())<520) Hero->ImpactCamera(.6f);
                const FVector To=Hero->GetActorLocation()-GetActorLocation();
                const bool InAngle=Stomp || FVector::DotProduct(To.GetSafeNormal2D(),GetActorForwardVector())>=FMath::Cos(FMath::DegreesToRadians(P->Angle*.5f));
                if (To.Size2D()<=P->Range && InAngle && HasClearContact())
                    Hero->ReceivePattern(P->Damage,SBCombat::CanParry(Action));
            }
        }
        // A parry or break can transition state synchronously while delivering this hit.
        if (Generation!=AttackGeneration) return;
        if (PatternElapsed>=P->Windup+P->Active) Telegraph->SetVisibility(false);
        if (PatternElapsed>=StateDuration) Enter(ESBKnightAction::Idle,0);
        return;
    }
    SelectOrChase(Dt);
}
void ASBKnight::UpdateChargeLane()
{
    constexpr int32 Dashes=24;
    const float Step=ChargeDistance/Dashes;
    const double Z=-GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+4.f;
    for (int32 Row=0; Row<3; ++Row)
        for (int32 I=0; I<Dashes; ++I)
        {
            const float Y=(Row-1)*65.f;
            const FVector Position((I+.5f)*Step,Y,Z);
            const FVector Scale(Step*(Row==1 ? .0035f:.0084f),Row==1 ? .03f:.065f,.018f);
            Telegraph->UpdateInstanceTransform(Row*Dashes+I,FTransform(FQuat::Identity,Position,Scale),false,Row==2 && I==Dashes-1,true);
        }
}
void ASBKnight::TickCharge(const FSBPattern& P,float Previous)
{
    if (PatternElapsed<P.Windup || Previous>=P.Windup+P.Active) return;
    if (Previous<P.Windup) ASBGroundDust::Kick(GetWorld(),GetCharacterMovement()->GetActorFeetLocation(),ChargeForward,128.f);
    Telegraph->SetVisibility(false);
    const float A=FMath::Clamp((Previous-P.Windup)/P.Active,0.f,1.f);
    const float B=FMath::Clamp((PatternElapsed-P.Windup)/P.Active,0.f,1.f);
    const FVector Start=GetActorLocation();
    FHitResult Block;
    if (!bChargeBlocked)
    {
        AddActorWorldOffset(ChargeForward*(B-A)*ChargeDistance,true,&Block);
        bChargeBlocked=Block.bBlockingHit;
    }
    // Use actual swept travel; a column stops the charge and protects anyone behind it.
    if (bImpactResolved || (bChargeBlocked && Block.GetActor()!=Hero)) return;
    const FVector End=GetActorLocation()+ChargeForward*37.f;
    FVector Target=Hero->GetActorLocation(); Target.Z=Start.Z;
    if (FMath::PointDistToSegmentSquared(Target,Start+ChargeForward*37.f,End)>FMath::Square(65.f) || !HasClearContact()) return;
    bImpactResolved=true;
    const float OldHP=Hero->Health;
    Hero->ReceivePattern(P.Damage,true);
    bChargeConnected=Hero->Health<OldHP;
    if (bChargeConnected) {PlayCue(TEXT("Shield"));Hero->ImpactCamera(.85f);}
}
void ASBKnight::TickWave(const FSBPattern& P,float Previous)
{
    constexpr float Inner=112.f,HalfWidth=12.f;
    const double Distance=FVector::Dist2D(GetActorLocation(),Hero->GetActorLocation());
    if (PatternElapsed<P.Windup)
    {
        UpdateRing(Inner,Inner*FMath::Lerp(.25f,.96f,PatternElapsed/P.Windup));
        PreviousWaveDistance=Distance; return;
    }
    if (Previous>=P.Windup+P.Active) return;
    if (Previous<P.Windup)
    {
        PlayCue(TEXT("Stomp"),.74f,.66f);
        ASBGroundDust::Kick(GetWorld(),GetCharacterMovement()->GetActorFeetLocation(),FVector::ZeroVector,250.f);
    }
    auto Radius=[&](float At){return FMath::Lerp(Inner,P.Range,FMath::Clamp((At-P.Windup)/P.Active,0.f,1.f));};
    const float Front=Radius(PatternElapsed);
    UpdateRing(Front+HalfWidth,Front-HalfWidth);
    const double Before=PreviousWaveDistance-Radius(Previous), After=Distance-Front;
    if (!bImpactResolved && FMath::Max(Before,After)>=-HalfWidth && FMath::Min(Before,After)<=HalfWidth)
    {
        bImpactResolved=true;
        Hero->ReceivePattern(P.Damage,false);
    }
    PreviousWaveDistance=Distance;
}
bool ASBKnight::HasClearContact() const
{
    if (!Hero) return false;
    if (FMath::Abs(Hero->GetActorLocation().Z-GetActorLocation().Z)>
        GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+Hero->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()) return false;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(BossContact),false,this);
    Query.AddIgnoredActor(Hero);
    FHitResult Hit;
    // World geometry must block melee; targeting capsules and VFX do not block this query.
    return !GetWorld()->LineTraceSingleByObjectType(Hit,GetActorLocation(),Hero->GetActorLocation(),
        FCollisionObjectQueryParams(ECC_WorldStatic),Query);
}
bool ASBKnight::IsRecoveryWindow() const
{
    const FSBPattern* P=CurrentPattern();
    return P && PatternElapsed>=P->Windup+P->Active && PatternElapsed<StateDuration;
}
bool ASBKnight::IsPunishWindow() const
{
    return CombatData && Action==ESBKnightAction::ShieldCharge && !bChargeConnected &&
        PatternElapsed>=CombatData->ShieldCharge.Windup+CombatData->ShieldCharge.Active;
}
void ASBKnight::UpdateRing(float OuterRadius,float InnerRadius)
{
    constexpr int32 Count=36;
    for (int32 J=0;J<2;++J)
    {
        float R=J==0 ? OuterRadius : InnerRadius;
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
    HitFeedbackRemaining=FMath::Max(0.f,HitFeedbackRemaining-Dt);
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
    auto TrackPlate=[&](UCapsuleComponent* Part,FName Bone,FName Fallback)
    {
        const FName Anchor=GetMesh()->DoesSocketExist(Bone) ? Bone : Fallback;
        if (GetMesh()->DoesSocketExist(Anchor)) Part->SetWorldLocation(GetMesh()->GetSocketLocation(Anchor));
    };
    if (!bShieldBroken) TrackPlate(Shield,TEXT("ShieldPlate"),TEXT("ForearmL"));
    if (!bKneeBroken) TrackPlate(Knee,TEXT("KneePlateL"),TEXT("ShinL"));
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
UCapsuleComponent* ASBKnight::PartCollider(ESBArmorPart Part) const
{
    switch (Part)
    {
    case ESBArmorPart::SwordArm: return Arm;
    case ESBArmorPart::Shield: return Shield;
    case ESBArmorPart::Knee: return Knee;
    default: return Body;
    }
}
FVector ASBKnight::PartPoint(ESBArmorPart Part) const {return PartCollider(Part)->GetComponentLocation();}
float ASBKnight::GetPartHealth(ESBArmorPart Part) const
{
    switch (Part)
    {
    case ESBArmorPart::SwordArm: return ArmHealth;
    case ESBArmorPart::Shield: return ShieldHealth;
    case ESBArmorPart::Knee: return KneeHealth;
    default: return Health;
    }
}
float ASBKnight::GetPartMaxHealth(ESBArmorPart Part) const
{
    switch (Part)
    {
    case ESBArmorPart::SwordArm: return 90;
    case ESBArmorPart::Shield: return CombatData ? CombatData->ShieldDurability : 75.f;
    case ESBArmorPart::Knee: return CombatData ? CombatData->KneeDurability : 65.f;
    default: return 400;
    }
}
bool ASBKnight::IsPartBroken(ESBArmorPart Part) const
{
    switch (Part)
    {
    case ESBArmorPart::SwordArm: return bArmBroken;
    case ESBArmorPart::Shield: return bShieldBroken;
    case ESBArmorPart::Knee: return bKneeBroken;
    default: return false;
    }
}
bool ASBKnight::TracePart(const FVector& From,const FVector& To,ESBArmorPart Part) const
{
    if (!bEncounterActive || Health<=0 || IsPartBroken(Part)) return false;
    FHitResult Hit;
    return PartCollider(Part)->SweepComponent(Hit,From,To,FQuat::Identity,FCollisionShape::MakeSphere(12.f));
}
void ASBKnight::OnParried()
{
    if (!bEncounterActive || !SBCombat::CanParry(Action) || Health<=0) return;
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
void ASBKnight::BreakPart(ESBArmorPart Part)
{
    ++BreakCount; LastBrokenPart=Part;
    FVector Source=PartPoint(Part);
    FName Bone, Cue;
    UStaticMesh* Debris=nullptr;
    switch (Part)
    {
    case ESBArmorPart::SwordArm:
        Bone=TEXT("UpperArmR");Cue=TEXT("Break");Debris=FallenBlade;
        if (GetMesh()->DoesSocketExist(TEXT("HandR"))) Source=GetMesh()->GetSocketLocation(TEXT("HandR"));
        break;
    case ESBArmorPart::Shield:
        Bone=TEXT("ShieldPlate");Cue=TEXT("ShieldBreak");
        Debris=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/SoulBreak/Characters/SM_FallenShield.SM_FallenShield"),nullptr,LOAD_NoWarn);
        break;
    case ESBArmorPart::Knee:
        Bone=TEXT("KneePlateL");Cue=TEXT("KneeBreak");
        Debris=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/SoulBreak/Characters/SM_FallenKnee.SM_FallenKnee"),nullptr,LOAD_NoWarn);
        GetCharacterMovement()->MaxWalkSpeed=150;
        break;
    default: return;
    }
    if (auto* Fx=GetWorld()->SpawnActor<ASBImpact>(Source,GetActorRotation()))
    {
        const float Side=Part==ESBArmorPart::SwordArm ? 1.f:-1.f;
        Fx->Launch(Debris,GetActorRightVector()*Side*125.f+FVector(0,0,102),
            GetActorLocation().Z-GetCapsuleComponent()->GetScaledCapsuleHalfHeight(),
            GetMesh()->GetRelativeScale3D().X,FLinearColor(1,.47,.08));
    }
    PartCollider(Part)->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    if (GetMesh()->DoesSocketExist(Bone)) GetMesh()->HideBoneByName(Bone,EPhysBodyOp::PBO_None);
    PlayCue(Cue,1.15f);
    if (Hero) Hero->ImpactCamera(1);
}
void ASBKnight::ApplySwordHit(int32 Id,float Damage,bool HitArm)
{
    ApplyPartHit(Id,Damage,HitArm ? ESBArmorPart::SwordArm : ESBArmorPart::Body);
}
void ASBKnight::ApplyPartHit(int32 Id,float Damage,ESBArmorPart Part)
{
    if (!bEncounterActive) return;
    const int32 OldPhase=Phase;
    float& Durability=Part==ESBArmorPart::Shield ? ShieldHealth : Part==ESBArmorPart::Knee ? KneeHealth : ArmHealth;
    bool& Broken=Part==ESBArmorPart::Shield ? bShieldBroken : Part==ESBArmorPart::Knee ? bKneeBroken : bArmBroken;
    const bool bHitArmor=Part!=ESBArmorPart::Body && !Broken;
    const ESBHitResult R=SBCombat::ResolvePart(Id,LastHitId,Damage,Part,Health,Durability,Broken,Phase,IsPunishWindow() ? 1.5f:1.f);
    if (R==ESBHitResult::Miss) return;
    LastHitPart=bHitArmor ? Part : ESBArmorPart::Body;
    HitFeedbackRemaining=.65f;
    HitPulse=1.f;
    PlayCue(bHitArmor ? TEXT("Shield") : TEXT("BodyHit"),bHitArmor ? .75f : .9f,bHitArmor ? 1.18f : .86f);
    if (R==ESBHitResult::Death)
    {
        StopMoving(); Enter(ESBKnightAction::Dead,1.25f); Pose(TEXT("Death"),false,1.25f,true);
        bEncounterActive=false; return;
    }
    if (R==ESBHitResult::Broken) BreakPart(Part);
    if (OldPhase!=Phase) { ++PhaseChanges; bPreferStomp=true; }
    if (R==ESBHitResult::Broken || R==ESBHitResult::Phase)
    {
        StopMoving();
        if (R==ESBHitResult::Broken && Part==ESBArmorPart::Shield)
        {
            Enter(ESBKnightAction::ShieldRecoil,1.f);
            Pose(TEXT("Stagger"),false,1.f,true);
            return;
        }
        Enter(OldPhase!=Phase ? ESBKnightAction::Transition : ESBKnightAction::Stagger,1.f);
        Pose(R==ESBHitResult::Broken && Part==ESBArmorPart::SwordArm ? TEXT("Sunder") : TEXT("Stagger"),false,1.f,true);
    }
    else if (auto* Fx=GetWorld()->SpawnActor<ASBImpact>(PartPoint(bHitArmor ? Part : ESBArmorPart::Body),GetActorRotation()))
        Fx->Launch(nullptr,FVector::ZeroVector,GetActorLocation().Z-GetCapsuleComponent()->GetScaledCapsuleHalfHeight(),1,
            bHitArmor ? FLinearColor(1,.6,.09) : FLinearColor(.25,.85,.95));
    UE_LOG(LogTemp,Display,TEXT("SoulBreak hit=%d hp=%.0f arm=%.0f shield=%.0f knee=%.0f phase=%d"),Id,Health,ArmHealth,ShieldHealth,KneeHealth,Phase);
}
