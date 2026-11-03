#include "Core/SBGameMode.h"
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
}

void ASBGameMode::StartPlay()
{
    Super::StartPlay();
    Hero = Cast<ASBHero>(UGameplayStatics::GetPlayerPawn(this, 0));
    FActorSpawnParameters Spawn;
    Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButAlwaysSpawn;
    Knight = GetWorld()->SpawnActor<ASBKnight>(KnightClass, FVector(350, 0, 158), FRotator(0, 180, 0), Spawn);
    Dummy = GetWorld()->SpawnActor<ASBTrainingDummy>(ASBTrainingDummy::StaticClass(),FVector(-755,218,1),FRotator::ZeroRotator,Spawn);
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
    if (Encounter == ESBEncounter::Approach && Hero->GetActorLocation().X >= -550)
    {
        Encounter = ESBEncounter::Fighting;
        Knight->StartEncounter(Hero);
    }
    if (Encounter == ESBEncounter::Fighting)
    {
        FightSeconds += DeltaSeconds;
        if (Knight->Health <= 0 || Hero->Health <= 0) Finish(Knight->Health <= 0);
    }
    else if (Encounter != ESBEncounter::Approach) OutcomeSeconds += DeltaSeconds;
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
