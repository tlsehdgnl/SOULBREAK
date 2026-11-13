#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "SBGameMode.generated.h"

class ASBTrainingDummy;
class ASBHero;
class ASBKnight;
class USoundBase;

UENUM(BlueprintType)
enum class ESBEncounter : uint8 { Approach, Fighting, Victory, Defeat, Introduction, Altar };

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
    bool CanLightCandle() const;
    bool CandleIsLit() const { return CandleTime>=0.f; }
    bool TryLightCandle();
    bool CanOpenDoor() const;
    bool TryOpenDoor();
    bool DoorIsOpen() const { return DoorTime>=1.2f; }
private:
    UPROPERTY() TObjectPtr<class ASBCathedralGate> Gate;
    UPROPERTY() TObjectPtr<class ACameraActor> IntroCamera;
    UPROPERTY() TObjectPtr<USoundBase> Roar;
    UPROPERTY() TObjectPtr<class UStaticMeshComponent> Flame;
    UPROPERTY() TObjectPtr<class UPointLightComponent> Candlelight;
    float CandleTime=-1.f;
    float DoorTime=-1.f;
    float IntroTime=0.f;
    void BeginIntroduction();
    void Finish(bool bVictory);
    UPROPERTY() TObjectPtr<USoundBase> VictoryCue;
    UPROPERTY() TObjectPtr<USoundBase> DefeatCue;
    UPROPERTY() TSubclassOf<ASBKnight> KnightClass;
    bool bReloading = false;
};
