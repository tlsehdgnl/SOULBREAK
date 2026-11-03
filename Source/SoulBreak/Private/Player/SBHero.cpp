#include "Player/SBHero.h"
#include "Boss/SBKnight.h"
#include "Combat/SBCombatComponent.h"
#include "Combat/SBTrainingDummy.h"
#include "Combat/SBImpact.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/SpringArmComponent.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "InputActionValue.h"
#include "Misc/App.h"
#include "InputAction.h"
#include "InputMappingContext.h"
#include "InputModifiers.h"

ASBHero::ASBHero()
{
    GetCapsuleComponent()->InitCapsuleSize(30,90);
    GetCharacterMovement()->MaxWalkSpeed = 450;
    GetCharacterMovement()->MaxAcceleration = 3400;
    GetCharacterMovement()->BrakingDecelerationWalking = 3000;
    Combat = CreateDefaultSubobject<USBCombatComponent>(TEXT("Combat"));
    Boom = CreateDefaultSubobject<USpringArmComponent>(TEXT("CameraBoom"));
    Boom->SetupAttachment(RootComponent);
    Boom->TargetArmLength=365;
    Boom->SetRelativeLocation(FVector(0,0,49));
    Boom->SocketOffset=FVector(0,42,8);
    Boom->bUsePawnControlRotation=true;
    Boom->bEnableCameraLag=true;
    Boom->CameraLagSpeed=17;
    Boom->ProbeSize=11;
    Camera=CreateDefaultSubobject<UCameraComponent>(TEXT("FollowCamera"));
    Camera->SetupAttachment(Boom,USpringArmComponent::SocketName);
    Camera->SetFieldOfView(76);
}
void ASBHero::BeginPlay()
{
    Super::BeginPlay();
    LoadFighter(TEXT("Hero"),184.f);
    if (AController* C=GetController()) C->SetControlRotation(FRotator(-9,GetActorRotation().Yaw,0));
}
void ASBHero::PawnClientRestart()
{
    Super::PawnClientRestart();
    if (Controller) Controller->SetControlRotation(FRotator(-9,GetActorRotation().Yaw,0));
    AcceptLookAfter = GetWorld()->GetTimeSeconds() + .25;
    bHasMouseSample = false;
}
void ASBHero::SetupPlayerInputComponent(UInputComponent* Input)
{
    Super::SetupPlayerInputComponent(Input);
    auto* IC=Cast<UEnhancedInputComponent>(Input);
    auto* PC=Cast<APlayerController>(GetController());
    if (!IC || !PC || !PC->GetLocalPlayer()) return;
    auto* Sys=ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(PC->GetLocalPlayer());
    if (!Sys) return;
    RemoveMapping();
    MappingOwner=Sys;
    Mapping=NewObject<UInputMappingContext>(this);
    auto MakeAxis=[&](const FKey Key,UInputAction* Act,bool bSwap,bool bNegate) {
        auto& M=Mapping->MapKey(Act,Key);
        if (bSwap) M.Modifiers.Add(NewObject<UInputModifierSwizzleAxis>(Mapping));
        if (bNegate) M.Modifiers.Add(NewObject<UInputModifierNegate>(Mapping));
    };
    MoveAction=NewObject<UInputAction>(Mapping);
    MoveAction->ValueType=EInputActionValueType::Axis2D;
    MoveAction->AccumulationBehavior=EInputActionAccumulationBehavior::Cumulative;
    MakeAxis(EKeys::W,MoveAction,true,false); MakeAxis(EKeys::S,MoveAction,true,true);
    MakeAxis(EKeys::D,MoveAction,false,false); MakeAxis(EKeys::A,MoveAction,false,true);
    LookAction=NewObject<UInputAction>(Mapping);
    LookAction->ValueType=EInputActionValueType::Axis2D;
    LookAction->AccumulationBehavior=EInputActionAccumulationBehavior::Cumulative;
    MakeAxis(EKeys::MouseX,LookAction,false,false); MakeAxis(EKeys::MouseY,LookAction,true,false);
    IC->BindAction(MoveAction,ETriggerEvent::Triggered,this,&ASBHero::MoveInput);
    IC->BindAction(MoveAction,ETriggerEvent::Completed,this,&ASBHero::MoveInput);
    IC->BindAction(LookAction,ETriggerEvent::Triggered,this,&ASBHero::LookInput);
    auto Button=[&](FKey Key) {
        UInputAction* Act=NewObject<UInputAction>(Mapping); Mapping->MapKey(Act,Key); return Act;
    };
    IC->BindAction(Button(EKeys::LeftMouseButton),ETriggerEvent::Started,this,&ASBHero::TryAttack);
    IC->BindAction(Button(EKeys::RightMouseButton),ETriggerEvent::Started,this,&ASBHero::TryParry);
    IC->BindAction(Button(EKeys::SpaceBar),ETriggerEvent::Started,this,&ASBHero::TryDodge);
    IC->BindAction(Button(EKeys::Tab),ETriggerEvent::Started,this,&ASBHero::ToggleLock);
    IC->BindAction(Button(EKeys::E),ETriggerEvent::Started,this,&ASBHero::TryOathCut);
    UInputAction* Sprint=Button(EKeys::LeftShift);
    IC->BindAction(Sprint,ETriggerEvent::Started,this,&ASBHero::SetSprinting,true);
    IC->BindAction(Sprint,ETriggerEvent::Completed,this,&ASBHero::SetSprinting,false);
    Sys->AddMappingContext(Mapping,10);
}
void ASBHero::RemoveMapping()
{
    if (MappingOwner.IsValid() && Mapping) MappingOwner->RemoveMappingContext(Mapping);
    MappingOwner.Reset();
}
void ASBHero::UnPossessed()
{
    RemoveMapping(); Stick=FVector2D::ZeroVector; bSprintHeld=false;
    Super::UnPossessed();
}
void ASBHero::EndPlay(EEndPlayReason::Type Why)
{
    RemoveMapping();
    Super::EndPlay(Why);
}
void ASBHero::SetKnight(ASBKnight* NewKnight) { Knight=NewKnight; if (!Knight) bLockedOn=false; }
void ASBHero::SetDummy(ASBTrainingDummy* NewDummy) {Dummy=NewDummy;}
void ASBHero::ToggleLock() { if (Health>0 && IsValid(Knight) && Knight->Health>0) bLockedOn=!bLockedOn; }
void ASBHero::SetMoveStick(FVector2D V) { Stick=V.GetClampedToMaxSize(1.f); }
void ASBHero::SetSprinting(bool Held) { bSprintHeld=Held; if (!Held) bNeedsSprintRecovery=false; }
void ASBHero::MoveInput(const FInputActionValue& V) { SetMoveStick(V.Get<FVector2D>()); }
void ASBHero::LookInput(const FInputActionValue& V)
{
    if (bLockedOn || !Controller || Health<=0) return;
    // On first capture the platform may report a warp from the desktop pointer to the viewport center.
    if (!FApp::HasFocus() || GetWorld()->GetTimeSeconds() < AcceptLookAfter)
    {
        bHasMouseSample = false;
        return;
    }
    if (!bHasMouseSample)
    {
        bHasMouseSample = true;
        return;
    }
    FVector2D Delta=V.Get<FVector2D>();
    FRotator Rot=Controller->GetControlRotation();
    Rot.Yaw+=Delta.X*1.25; Rot.Pitch=FMath::ClampAngle(Rot.Pitch+Delta.Y*1.15,-62.f,38.f);
    Controller->SetControlRotation(Rot);
}
FVector ASBHero::WishDirection() const
{
    const FRotationMatrix Basis(FRotator(0,GetControlRotation().Yaw,0));
    return Basis.GetUnitAxis(EAxis::X)*Stick.Y + Basis.GetUnitAxis(EAxis::Y)*Stick.X;
}
bool ASBHero::Spend(float Cost)
{
    if (!SBCombat::Spend(Stamina,Cost)) return false;
    SpentAt=GetWorld()->TimeSeconds; return true;
}
void ASBHero::BeginAction(ESBHeroAction Next,FName Clip,float Duration)
{
    Action=Next; ActionElapsed=0; bQueuedCombo=false; Combat->Cancel();
    GetCharacterMovement()->StopMovementImmediately();
    Pose(Clip,false,Duration,true);
}
void ASBHero::BeginCut(bool bSecond)
{
    const FSBAttackTiming& W=bSecond ? CombatData->ReturnCut : CombatData->Cut;
    if (!Spend(W.Cost)) return;
    if (bLockedOn && Knight) Face(Knight->GetActorLocation()-GetActorLocation(),180);
    else if (!Stick.IsNearlyZero()) Face(WishDirection(),180);
    BeginAction(bSecond ? ESBHeroAction::ReturnCut:ESBHeroAction::Cut,bSecond ? TEXT("ReturnCut"):TEXT("Cut"),W.Duration);
    Combat->StartCut();
    PlayCue(TEXT("Swing"),.68f,bSecond ? .88f:1.06f);
}
void ASBHero::TryAttack()
{
    if (!CombatData || Health<=0) return;
    if (Action==ESBHeroAction::Cut && ActionElapsed>=CombatData->Cut.Duration-.20f) { bQueuedCombo=true; return; }
    if (Action==ESBHeroAction::Ready) BeginCut(false);
}
void ASBHero::TryOathCut()
{
    if (!CombatData || !bOathReady || Health<=0 || Action!=ESBHeroAction::Ready) return;
    bOathReady=false;
    if (bLockedOn && Knight) Face(Knight->GetActorLocation()-GetActorLocation(),180);
    BeginAction(ESBHeroAction::OathCut,TEXT("OathCut"),CombatData->OathCut.Duration);
    Combat->StartCut(); PlayCue(TEXT("Parry"),.72f,.76f);
}
void ASBHero::TryDodge()
{
    if (!CombatData || Action!=ESBHeroAction::Ready || !Spend(CombatData->Evade.Cost)) return;
    DodgeDirection=Stick.IsNearlyZero() ? GetActorForwardVector():WishDirection().GetSafeNormal2D();
    Face(DodgeDirection,180);
    BeginAction(ESBHeroAction::Evade,TEXT("Evade"),CombatData->Evade.Duration);
    PlayCue(TEXT("Dodge"),.7f);
}
void ASBHero::TryParry()
{
    if (!CombatData || Action!=ESBHeroAction::Ready || !Spend(CombatData->Parry.Cost)) return;
    BeginAction(ESBHeroAction::Parry,TEXT("Parry"),CombatData->Parry.Duration);
    PlayCue(TEXT("Shield"),.26f,1.32f);
}
void ASBHero::ReceivePattern(float Damage,bool bSword)
{
    if (Health<=0 || Damage<=0) return;
    if (Action==ESBHeroAction::Evade && SBCombat::InWindow(ActionElapsed,CombatData->Evade)) { ++DodgedHits; return; }
    if (bSword && Action==ESBHeroAction::Parry && SBCombat::InWindow(ActionElapsed,CombatData->Parry))
    {
        ++SuccessfulParries; bOathReady=true; ParryPulse=1.f; ImpactCamera(.85f); PlayCue(TEXT("Parry"));
        if (Knight) Knight->OnParried(); return;
    }
    Health=FMath::Max(0.f,Health-Damage); HitPulse=1.f; ImpactCamera(.7f);
    PlayCue(TEXT("BodyHit"));
    if (Health<=0) { bLockedOn=false; BeginAction(ESBHeroAction::Dead,TEXT("Death"),1.25f); }
    else BeginAction(ESBHeroAction::Hurt,TEXT("Stagger"),.40f);
}
void ASBHero::ImpactCamera(float Strength) { Shake=FMath::Max(Shake,Strength); }
void ASBHero::UpdateCamera(float Dt)
{
    if (IsValid(Knight) && Knight->Health<=0) bLockedOn=false;
    if (bLockedOn && Controller && Knight)
    {
        FVector Focus=Knight->GetActorLocation()+FVector(0,0,27);
        FRotator Desired=(Focus-(GetActorLocation()+FVector(0,0,48))).Rotation();
        // An oblique view keeps the weapon arm visible when both fighters are within striking distance.
        const float Near = 1.f-FMath::Clamp((FVector::Dist2D(Focus,GetActorLocation())-82.f)/265.f,0.f,1.f);
        Desired.Yaw += 37.f*Near;
        Desired.Pitch = FMath::Clamp(Desired.Pitch*.42f-9.f-5.f*Near,-22.f,9.f);
        Controller->SetControlRotation(FMath::RInterpTo(Controller->GetControlRotation(),Desired,Dt,11));
    }
    Shake=FMath::Max(0.f,Shake-Dt*3.6f);
    const float T=GetWorld()->TimeSeconds;
    Camera->SetRelativeLocation(FVector(0,4.5f*Shake*FMath::Sin(T*106),3.2f*Shake*FMath::Sin(T*87)));
    Boom->TargetArmLength=FMath::FInterpTo(Boom->TargetArmLength,bLockedOn ? 460.f : 365.f,Dt,5);
}
void ASBHero::Tick(float Dt)
{
    Super::Tick(Dt); UpdateCamera(Dt);
    if (!CombatData) return;
    ParryPulse=FMath::Max(0.f,ParryPulse-Dt*1.8f);
    float Previous=ActionElapsed;
    ActionElapsed+=Dt;
    if (Action==ESBHeroAction::Dead) return;
    const bool bMoving=!Stick.IsNearlyZero();
    const bool bSprint=bMoving && bSprintHeld && !bNeedsSprintRecovery && Action==ESBHeroAction::Ready;
    if (bSprint && !Spend(Dt*CombatData->SprintCost)) bNeedsSprintRecovery=true;
    if (GetWorld()->TimeSeconds-SpentAt>CombatData->RegenDelay)
        Stamina=FMath::Min(100.f,Stamina+Dt*CombatData->RegenRate);
    switch(Action)
    {
    case ESBHeroAction::Ready:
        GetCharacterMovement()->MaxWalkSpeed=bSprint && !bNeedsSprintRecovery ? 650.f : 450.f;
        if (bMoving) AddMovementInput(WishDirection());
        if (bLockedOn && Knight) Face(Knight->GetActorLocation()-GetActorLocation(),720*Dt);
        else if (bMoving) Face(WishDirection(),780*Dt);
        Locomotion(450.f);
        break;
    case ESBHeroAction::Cut:
    case ESBHeroAction::ReturnCut:
    case ESBHeroAction::OathCut:
    {
        const bool Second=Action==ESBHeroAction::ReturnCut;
        const bool Oath=Action==ESBHeroAction::OathCut;
        const FSBAttackTiming& W=Oath ? CombatData->OathCut : Second ? CombatData->ReturnCut : CombatData->Cut;
        if (Oath && Previous<W.Open && ActionElapsed>=W.Open)
        {
            PlayCue(TEXT("Swing"),1.2f,.70f); ImpactCamera(.42f);
            for (float Degrees : {-53.f,0.f,53.f})
            {
                const FVector P=GetActorLocation()+GetActorForwardVector().RotateAngleAxis(Degrees,FVector::UpVector)*93.f+FVector(0,0,41);
                if (auto* FX=GetWorld()->SpawnActor<ASBImpact>(P,GetActorRotation()))
                    FX->Launch(nullptr,FVector::ZeroVector,GetActorLocation().Z-90,1,FLinearColor(.13,1.5,1.25),1.35f);
            }
        }
        const float Step=FMath::Min(ActionElapsed,.14f)-FMath::Min(Previous,.14f);
        if (Step>0) AddActorWorldOffset(GetActorForwardVector()*Step*165.f,true);
        Combat->TraceCut(*this,Knight,Dummy,W,Second,Previous,ActionElapsed);
        if (ActionElapsed>=W.Duration)
        {
            const bool Chain=bQueuedCombo && !Second; bQueuedCombo=false; Combat->Cancel();
            Action=ESBHeroAction::Ready;
            if (Chain) BeginCut(true);
        }
        break;
    }
    case ESBHeroAction::Evade:
    {
        float Duration=CombatData->Evade.Duration;
        float P=FMath::Clamp(Previous/Duration,0.f,1.f),T=FMath::Clamp(ActionElapsed/Duration,0.f,1.f);
        // Cosine easing keeps the whole 280 cm displacement independent of frame rate.
        float Travel=.5f*(FMath::Cos(P*PI)-FMath::Cos(T*PI));
        AddActorWorldOffset(DodgeDirection*280.f*Travel,true);
        if (T>=1) Action=ESBHeroAction::Ready;
        break;
    }
    case ESBHeroAction::Parry: if (ActionElapsed>=CombatData->Parry.Duration) Action=ESBHeroAction::Ready; break;
    case ESBHeroAction::Hurt: if (ActionElapsed>=.4f) Action=ESBHeroAction::Ready; break;
    default: break;
    }
}
