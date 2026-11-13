#include "Core/SBGameMode.h"
#include "Core/SBCathedralGate.h"
#include "Camera/CameraActor.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Materials/MaterialInterface.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Combat/SBTrainingDummy.h"
#include "Core/SBPlayerController.h"
#include "Tests/SBReviewDriver.h"
#include "Misc/CommandLine.h"
#include "UI/SBCombatHUD.h"
#include "Player/SBHero.h"
#include "Boss/SBKnight.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"
#include "UObject/ConstructorHelpers.h"

ASBGameMode::ASBGameMode()
{
    PrimaryActorTick.bCanEverTick = true;
    DefaultPawnClass = ASBHero::StaticClass();
    KnightClass = ASBKnight::StaticClass();
    static ConstructorHelpers::FClassFinder<ASBHero> HeroBP(TEXT("/Game/SoulBreak/Characters/BP_Hero"));
    static ConstructorHelpers::FClassFinder<ASBKnight> KnightBP(TEXT("/Game/SoulBreak/Characters/BP_Knight"));
    if (HeroBP.Succeeded()) DefaultPawnClass = HeroBP.Class;
    if (KnightBP.Succeeded()) KnightClass = KnightBP.Class;
    HUDClass = ASBCombatHUD::StaticClass();
    PlayerControllerClass = ASBPlayerController::StaticClass();
    static ConstructorHelpers::FObjectFinderOptional<USoundBase> Victory(TEXT("/Game/SoulBreak/Audio/S_Victory"));
    static ConstructorHelpers::FObjectFinderOptional<USoundBase> Defeat(TEXT("/Game/SoulBreak/Audio/S_Defeat"));
    VictoryCue = Victory.Get();
    DefeatCue = Defeat.Get();
    static ConstructorHelpers::FObjectFinder<USoundBase> Voice(TEXT("/Game/SoulBreak/Audio/S_KnightRoar"));
    Roar=Voice.Object;
}

void ASBGameMode::StartPlay()
{
    Super::StartPlay();
    Hero = Cast<ASBHero>(UGameplayStatics::GetPlayerPawn(this, 0));
    FActorSpawnParameters Spawn;
    Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButAlwaysSpawn;
    Knight = GetWorld()->SpawnActor<ASBKnight>(KnightClass, FVector(350, 0, 158), FRotator(0, 180, 0), Spawn);
    Gate=GetWorld()->SpawnActor<ASBCathedralGate>(FVector(-1110,0,0),FRotator::ZeroRotator);
    Dummy = GetWorld()->SpawnActor<ASBTrainingDummy>(ASBTrainingDummy::StaticClass(),FVector(-1860,-80,1),FRotator::ZeroRotator,Spawn);
    auto* Candle=GetWorld()->SpawnActor<AActor>(FVector(1012,58,64),FRotator::ZeroRotator);
    auto Piece=[&](const TCHAR* Shape,const TCHAR* Surface,FVector Scale,float Height)
    {
        auto* Mesh=NewObject<UStaticMeshComponent>(Candle);
        Mesh->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,Shape));
        Mesh->SetMaterial(0,LoadObject<UMaterialInterface>(nullptr,Surface));
        Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        if (!Candle->GetRootComponent()) Candle->SetRootComponent(Mesh);
        else Mesh->AttachToComponent(Candle->GetRootComponent(),FAttachmentTransformRules::KeepWorldTransform);
        Mesh->SetWorldLocation(FVector(1012,58,64+Height));
        Mesh->SetWorldScale3D(Scale);
        Mesh->RegisterComponent();
        return Mesh;
    };
    Piece(TEXT("/Engine/BasicShapes/Cylinder"),TEXT("/Game/SoulBreak/Materials/Characters/MI_Bronze"),{.21,.21,.045},2);
    Piece(TEXT("/Engine/BasicShapes/Cylinder"),TEXT("/Game/SoulBreak/Materials/Characters/MI_Ivory"),{.088,.088,.28},18);
    Flame=Piece(TEXT("/Engine/BasicShapes/Sphere"),TEXT("/Game/SoulBreak/Materials/Characters/MI_Flame"),{.045,.045,.13},38);
    Flame->SetVisibility(false);
    Candlelight=NewObject<UPointLightComponent>(Candle);
    Candlelight->SetupAttachment(Flame);
    Candlelight->SetLightColor(FLinearColor(1,.49f,.16f));
    Candlelight->SetAttenuationRadius(360.f);
    Candlelight->SetIntensity(0);
    Candlelight->RegisterComponent();
    if (Hero) { Hero->SetKnight(Knight); Hero->SetDummy(Dummy); }
#if !UE_BUILD_SHIPPING && !UE_BUILD_TEST
    if (FParse::Param(FCommandLine::Get(),TEXT("SBDemo")) || FParse::Param(FCommandLine::Get(),TEXT("SBPerf")))
        GetWorld()->SpawnActor<ASBReviewDriver>();
    if (FParse::Param(FCommandLine::Get(),TEXT("SBAudit")))
        if (UClass* Audit = LoadClass<AActor>(nullptr,TEXT("/Script/SoulBreak.SBScenarioAudit"))) GetWorld()->SpawnActor<AActor>(Audit);
#endif
}
void ASBGameMode::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (!Hero)
    {
        Hero = Cast<ASBHero>(UGameplayStatics::GetPlayerPawn(this, 0));
        if (Hero) { Hero->SetKnight(Knight); Hero->SetDummy(Dummy); }
    }
    if (!Hero || !Knight) return;
    if (Encounter==ESBEncounter::Approach && Gate && DoorTime>=0.f && !DoorIsOpen())
    {
        DoorTime=FMath::Min(1.2f,DoorTime+DeltaSeconds);
        Gate->SetOpening(DoorTime/1.2f);
    }
    if (Encounter==ESBEncounter::Approach && Gate && DoorTime>=0.f)
    {
        const FVector Local=Gate->GetActorTransform().InverseTransformPosition(Hero->GetActorLocation());
        // A player holding sprint can pass the moving leaves before the opening animation ends.
        if (Local.X>=92 && Local.X<=2120 && FMath::Abs(Local.Y)<=1010)
            BeginIntroduction();
    }
    if (Encounter==ESBEncounter::Introduction)
    {
        const float Previous=IntroTime;
        IntroTime+=DeltaSeconds;
        Gate->SetOpening((DoorTime/1.2f)*(1.f-FMath::Clamp(IntroTime/.52f,0.f,1.f)));
        auto* PC=GetWorld()->GetFirstPlayerController();
        if (Previous<1.05f && IntroTime>=1.05f)
        {
            Knight->RoarPose();
            UGameplayStatics::PlaySoundAtLocation(this,Roar,Knight->GetActorLocation());
        }
        if (Previous<2.7f && IntroTime>=2.7f) PC->SetViewTargetWithBlend(Hero,.65f,VTBlend_EaseInOut,2.f);
        if (IntroTime>=3.4f)
        {
            PC->SetViewTarget(Hero);
            Hero->EnableInput(PC);
            if (IntroCamera) IntroCamera->Destroy();
            Encounter=ESBEncounter::Fighting;
            DoorTime=-1.f;
            Knight->StartEncounter(Hero);
        }
        return;
    }
    if (Encounter == ESBEncounter::Fighting)
    {
        FightSeconds += DeltaSeconds;
        if (Knight->Health<=0)
        {
            if (Knight->PatternElapsed>=(Knight->bOathFinish ? 1.63f : 1.25f))
            {
                Encounter=ESBEncounter::Altar;
                OutcomeSeconds=0;
                Gate->UnsealPassage();
            }
        }
        else if (Hero->Health<=0) Finish(false);
    }
    else if (Encounter==ESBEncounter::Altar)
    {
        OutcomeSeconds+=DeltaSeconds;
        Gate->SetOpening(FMath::Min(1.f,OutcomeSeconds/1.2f));
        if (CandleTime>=0)
        {
            CandleTime+=DeltaSeconds;
            Candlelight->SetIntensity(180.f*FMath::Min(1.f,CandleTime/.45f));
            if (CandleTime>=1.2f) { OutcomeSeconds=0; Finish(true); }
        }
    }
    else if (Encounter != ESBEncounter::Approach) OutcomeSeconds += DeltaSeconds;
}
bool ASBGameMode::CanLightCandle() const
{
    return Encounter==ESBEncounter::Altar && CandleTime<0 && !bHelpOpen && Hero && Flame &&
        FVector::Dist2D(Hero->GetActorLocation(),Flame->GetComponentLocation())<150;
}
bool ASBGameMode::TryLightCandle()
{
    if (!CanLightCandle()) return false;
    CandleTime=0;
    Flame->SetVisibility(true);
    return true;
}
bool ASBGameMode::CanOpenDoor() const
{
    if (!Hero || !Gate || Encounter!=ESBEncounter::Approach || DoorTime>=0.f || bHelpOpen) return false;
    const FVector Local=Gate->GetActorTransform().InverseTransformPosition(Hero->GetActorLocation());
    return Local.X>=-170 && Local.X<=0 && FMath::Abs(Local.Y)<155;
}
bool ASBGameMode::TryOpenDoor()
{
    if (!CanOpenDoor()) return false;
    DoorTime=0;
    auto* Sound=LoadObject<USoundBase>(nullptr,TEXT("/Game/SoulBreak/Audio/S_Charge.S_Charge"));
    UGameplayStatics::PlaySoundAtLocation(this,Sound,Gate->GetActorLocation(),.8f,.62f);
    return true;
}
void ASBGameMode::BeginIntroduction()
{
    auto* PC=GetWorld()->GetFirstPlayerController();
    if (!PC) return;
    const FVector Focus=Knight->GetActorLocation()+FVector(0,0,52);
    const FVector CameraPosition=Focus+FVector(-310,-115,-35);
    IntroCamera=GetWorld()->SpawnActor<ACameraActor>(CameraPosition,(Focus-CameraPosition).Rotation());
    if (!IntroCamera) return;
    Encounter=ESBEncounter::Introduction;
    Gate->SealPassage();
    Hero->bLockedOn=false;
    Hero->SelectedPart=ESBArmorPart::Body;
    Hero->DisableInput(PC);
    Hero->GetCharacterMovement()->StopMovementImmediately();
    PC->SetControlRotation(FRotator(-8,0,0));
    Knight->RaiseGuard();
    PC->SetViewTargetWithBlend(IntroCamera,1.05f,VTBlend_EaseInOut,2.f);
}
void ASBGameMode::Finish(bool bVictory)
{
    Encounter = bVictory ? ESBEncounter::Victory : ESBEncounter::Defeat;
    Knight->StopEncounter();
    Hero->SetMoveStick(FVector2D::ZeroVector);
    Hero->SetSprinting(false);
    if (auto* PC=Cast<ASBPlayerController>(Hero->GetController()))
    {
        Hero->DisableInput(PC);
        PC->ShowOverlay(true,false);
    }
    if (USoundBase* Cue = bVictory ? VictoryCue.Get() : DefeatCue.Get()) UGameplayStatics::PlaySound2D(this, Cue);
    UE_LOG(LogTemp, Display, TEXT("SoulBreak encounter %s, %.2fs; boss %.0f arm %.0f hero %.0f"),
        bVictory ? TEXT("victory") : TEXT("defeat"), FightSeconds, Knight->Health, Knight->ArmHealth, Hero->Health);
}
void ASBGameMode::Retry()
{
    if (bReloading || (!bHelpOpen && Encounter != ESBEncounter::Victory && Encounter != ESBEncounter::Defeat)) return;
    bReloading = true;
    UGameplayStatics::SetGamePaused(this, false);
    UGameplayStatics::OpenLevel(this, FName(*UGameplayStatics::GetCurrentLevelName(this)));
}
void ASBGameMode::ToggleHelp()
{
    if (bReloading || Encounter == ESBEncounter::Victory || Encounter == ESBEncounter::Defeat) return;
    if (UGameplayStatics::SetGamePaused(this, !bHelpOpen))
    {
        bHelpOpen = !bHelpOpen;
        if (auto* PC=Cast<ASBPlayerController>(GetWorld()->GetFirstPlayerController())) PC->ShowOverlay(bHelpOpen,true);
    }
}
