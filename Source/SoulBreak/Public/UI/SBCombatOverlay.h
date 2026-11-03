#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "SBCombatOverlay.generated.h"

class UHorizontalBox;

UCLASS()
class SOULBREAK_API USBCombatOverlay : public UUserWidget
{
    GENERATED_BODY()
public:
    void ShowActions(bool bPaused);
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="Presentation") FLinearColor ButtonTint = FLinearColor(.07f,.13f,.15f,1.f);
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="Presentation") FLinearColor LabelTint = FLinearColor(.98f,.86f,.63f,1.f);
protected:
    virtual TSharedRef<SWidget> RebuildWidget() override;
private:
    UPROPERTY(Transient) TObjectPtr<UHorizontalBox> Commands;
    UFUNCTION() void Resume();
    UFUNCTION() void Retry();
    UFUNCTION() void Quit();
};
