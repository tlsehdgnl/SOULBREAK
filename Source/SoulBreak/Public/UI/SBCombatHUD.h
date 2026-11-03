#pragma once
#include "CoreMinimal.h"
#include "GameFramework/HUD.h"
#include "SBCombatHUD.generated.h"

class ASBGameMode;
UCLASS()
class SOULBREAK_API ASBCombatHUD : public AHUD
{
    GENERATED_BODY()
public:
    virtual void DrawHUD() override;
private:
    float Unit = 1, W = 0, H = 0;
    void Box(float X,float Y,float Width,float Height,FLinearColor Color);
    void Line(float X,float Y,float X2,float Y2,FLinearColor Color,float Weight = 1);
    void Label(const FString& Text,float X,float Y,float Size,FLinearColor Color,bool Center=false);
    void Diamond(float X,float Y,float R,FLinearColor Color);
    void Meter(float X,float Y,float Width,float Height,float Value,float Max,FLinearColor Color);
    void Vitals(const ASBGameMode& Game);
    void Encounter(const ASBGameMode& Game);
    void Guide();
    void Result(const ASBGameMode& Game);
    float ArmNoticeUntil = -1;
    bool bSawBreak = false;
};
