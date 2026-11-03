#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Data/SBCombatData.h"
#include "SBCombatComponent.generated.h"

class ASBKnight;
class ASBTrainingDummy;
class ASBHero;

// The timing driver traces an interpolated cutting arc. Accumulate contacts for the entire
// swing so a torso overlap on an earlier frame cannot steal a later arm contact.
UCLASS()
class SOULBREAK_API USBCombatComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    void StartCut();
    void Cancel();
    void TraceCut(ASBHero& Hero, ASBKnight* Knight, ASBTrainingDummy* Dummy, const FSBAttackTiming& Timing, bool bReverse, float Previous, float Now);
    UPROPERTY(BlueprintReadOnly) int32 AttackId = 0;
private:
    bool bBodyPending = false;
    bool bResolved = false;
};
