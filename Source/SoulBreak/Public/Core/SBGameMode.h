#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "SBGameMode.generated.h"

class ASBTrainingDummy;
class ASBHero;
class ASBKnight;
class USoundBase;

UENUM(BlueprintType)
enum class ESBEncounter : uint8 { Approach, Fighting, Victory, Defeat };

UCLASS()
class SOULBREAK_API ASBGameMode : public AGameModeBase
{
    GENERATED_BODY()
public:
    ASBGameMode();
    virtual void StartPlay() override;
    virtual void Tick(float DeltaSeconds) override;

    UPROPERTY(BlueprintReadOnly) TObjectPtr<ASBHero> Hero;
    UPROPERTY(BlueprintReadOnly) TObjectPtr<ASBKnight> Knight;
    UPROPERTY(BlueprintReadOnly) TObjectPtr<ASBTrainingDummy> Dummy;
    UPROPERTY(BlueprintReadOnly) ESBEncounter Encounter = ESBEncounter::Approach;
    UPROPERTY(BlueprintReadOnly) float FightSeconds = 0;
    UPROPERTY(BlueprintReadOnly) float OutcomeSeconds = 0;
    bool bHelpOpen = false;

    void Retry();
    void ToggleHelp();
private:
    void Finish(bool bVictory);
    UPROPERTY() TObjectPtr<USoundBase> VictoryCue;
    UPROPERTY() TObjectPtr<USoundBase> DefeatCue;
    UPROPERTY() TSubclassOf<ASBKnight> KnightClass;
    bool bReloading = false;
};
