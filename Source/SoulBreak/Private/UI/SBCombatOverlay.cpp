#include "UI/SBCombatOverlay.h"
#include "Core/SBPlayerController.h"
#include "Blueprint/WidgetTree.h"
#include "Components/Button.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/TextBlock.h"

TSharedRef<SWidget> USBCombatOverlay::RebuildWidget()
{
    if (WidgetTree && !Commands)
    {
        UCanvasPanel* Root=Cast<UCanvasPanel>(WidgetTree->RootWidget);
        if (!Root)
        {
            Root=WidgetTree->ConstructWidget<UCanvasPanel>();
            WidgetTree->RootWidget=Root;
        }
        Commands=WidgetTree->ConstructWidget<UHorizontalBox>();
        UCanvasPanelSlot* Position=Root->AddChildToCanvas(Commands);
        Position->SetAnchors(FAnchors(.5f,.86f));
        Position->SetAlignment(FVector2D(.5f,.5f));
        Position->SetAutoSize(true);
        Position->SetPosition(FVector2D::ZeroVector);
    }
    return Super::RebuildWidget();
}
void USBCombatOverlay::ShowActions(bool bPaused)
{
    if (!Commands) return;
    Commands->ClearChildren();
    auto Add=[&](const TCHAR* Caption)
    {
        auto* Button=WidgetTree->ConstructWidget<UButton>();
        Button->SetBackgroundColor(ButtonTint);
        Button->SetClickMethod(EButtonClickMethod::DownAndUp);
        auto* Label=WidgetTree->ConstructWidget<UTextBlock>();
        Label->SetText(FText::FromString(Caption));
        Label->SetColorAndOpacity(FSlateColor(LabelTint));
        FSlateFontInfo Font=Label->GetFont(); Font.Size=17; Label->SetFont(Font);
        Label->SetMargin(FMargin(17,8));
        Button->AddChild(Label);
        Commands->AddChildToHorizontalBox(Button)->SetPadding(FMargin(4,0));
        return Button;
    };
    if (bPaused) Add(TEXT("계속  ·  F1"))->OnClicked.AddDynamic(this,&USBCombatOverlay::Resume);
    Add(TEXT("재도전  ·  R"))->OnClicked.AddDynamic(this,&USBCombatOverlay::Retry);
    Add(TEXT("게임 종료  ·  Q"))->OnClicked.AddDynamic(this,&USBCombatOverlay::Quit);
}
void USBCombatOverlay::Resume() { if (auto* PC=Cast<ASBPlayerController>(GetOwningPlayer())) PC->ToggleHelp(); }
void USBCombatOverlay::Retry() { if (auto* PC=Cast<ASBPlayerController>(GetOwningPlayer())) PC->Retry(); }
void USBCombatOverlay::Quit() { if (auto* PC=Cast<ASBPlayerController>(GetOwningPlayer())) PC->LeaveGame(); }
