#include "Core/SBPlayerController.h"
#include "Core/SBGameMode.h"
#include "UI/SBCombatOverlay.h"
#include "Kismet/KismetSystemLibrary.h"

void ASBPlayerController::BeginPlay()
{
    Super::BeginPlay();
    SetInputMode(FInputModeGameOnly());
}
void ASBPlayerController::SetupInputComponent()
{
    Super::SetupInputComponent();
    InputComponent->BindKey(EKeys::R, IE_Pressed, this, &ASBPlayerController::Retry).bExecuteWhenPaused = true;
    InputComponent->BindKey(EKeys::Escape, IE_Pressed, this, &ASBPlayerController::ToggleHelp).bExecuteWhenPaused = true;
    InputComponent->BindKey(EKeys::F1, IE_Pressed, this, &ASBPlayerController::ToggleHelp).bExecuteWhenPaused = true;
    InputComponent->BindKey(EKeys::Q, IE_Pressed, this, &ASBPlayerController::LeaveGame).bExecuteWhenPaused = true;
}
void ASBPlayerController::Retry()
{
    if (ASBGameMode* Mode = GetWorld()->GetAuthGameMode<ASBGameMode>()) Mode->Retry();
}
void ASBPlayerController::ToggleHelp()
{
    if (ASBGameMode* Mode = GetWorld()->GetAuthGameMode<ASBGameMode>()) Mode->ToggleHelp();
}
void ASBPlayerController::LeaveGame()
{
    const ASBGameMode* Mode = GetWorld()->GetAuthGameMode<ASBGameMode>();
    if (Mode && (Mode->bHelpOpen || Mode->Encounter == ESBEncounter::Victory || Mode->Encounter == ESBEncounter::Defeat))
        UKismetSystemLibrary::QuitGame(this, this, EQuitPreference::Quit, false);
}

void ASBPlayerController::ShowOverlay(bool bVisible,bool bPaused)
{
    if (IsLocalController() && bVisible)
    {
        if (!Overlay)
        {
            auto Class=LoadClass<USBCombatOverlay>(nullptr,TEXT("/Game/SoulBreak/UI/WBP_Combat.WBP_Combat_C"));
            Overlay=CreateWidget<USBCombatOverlay>(this,Class ? Class : USBCombatOverlay::StaticClass());
            if (Overlay) Overlay->AddToViewport();
        }
        if (Overlay)
        {
            Overlay->SetVisibility(ESlateVisibility::SelfHitTestInvisible);
            Overlay->ShowActions(bPaused);
        }
        FInputModeGameAndUI Mode;
        Mode.SetHideCursorDuringCapture(false);
        Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
        SetInputMode(Mode);
        bShowMouseCursor=true;
        return;
    }
    if (Overlay) Overlay->SetVisibility(ESlateVisibility::Collapsed);
    bShowMouseCursor=false;
    SetInputMode(FInputModeGameOnly());
}
