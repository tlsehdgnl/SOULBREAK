#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SBTrainingDummy.generated.h"

class UStaticMeshComponent;
class USoundBase;

UCLASS()
class SOULBREAK_API ASBTrainingDummy : public AActor
{
    GENERATED_BODY()
public:
    ASBTrainingDummy();
    virtual void Tick(float DeltaSeconds) override;
    bool TraceSword(const FVector& From,const FVector& To) const;
    void ApplySwordHit(int32 AttackId,float Damage);
    UPROPERTY(BlueprintReadOnly) float Health = 100.f;
    UPROPERTY(BlueprintReadOnly) float HitPulse = 0.f;
private:
    UPROPERTY() TObjectPtr<USceneComponent> Target;
    UPROPERTY() TObjectPtr<USoundBase> Impact;
    int32 LastHitId = 0;
    float RestSeconds = 0;
};
