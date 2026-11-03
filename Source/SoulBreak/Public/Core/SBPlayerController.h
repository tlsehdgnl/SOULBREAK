#pragma once
#include "CoreMinimal.h"
#include "GameFramework/PlayerController.h"
#include "SBPlayerController.generated.h"

class USBCombatOverlay;

UCLASS()
class SOULBREAK_API ASBPlayerController : public APlayerController
{
    GENERATED_BODY()
public:
    virtual void SetupInputComponent() override;
    virtual void BeginPlay() override;
    void ShowOverlay(bool bVisible, bool bPaused);
    void Retry();
    void ToggleHelp();
    void LeaveGame();
private:
    UPROPERTY(Transient) TObjectPtr<USBCombatOverlay> Overlay;
};
