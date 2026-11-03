#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SBScenarioAudit.generated.h"

// Development executable integration audit. The game mode spawns it only on -SBAudit.
UCLASS(NotBlueprintable, Transient)
class SOULBREAK_API ASBScenarioAudit : public AActor
{
    GENERATED_BODY()
public:
    ASBScenarioAudit();
    virtual void Tick(float Dt) override;
private:
    int32 Step = 0;
    float Clock = 0;
    FVector StartPosition = FVector::ZeroVector;
    double ExpectedDefenseStart = 0;
    int32 PreviousGeneration = -1;
    int32 Observed = 0;
    bool bSawSword = false;
    bool bSawStomp = false;
    bool bSawBash = false;
    TArray<FKey> Releases;
};
