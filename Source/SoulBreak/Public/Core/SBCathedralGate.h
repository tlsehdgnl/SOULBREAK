#pragma once
#include "GameFramework/Actor.h"
#include "SBCathedralGate.generated.h"

class USceneComponent;
UCLASS()
class SOULBREAK_API ASBCathedralGate : public AActor
{
    GENERATED_BODY()
public:
    ASBCathedralGate();
    void SetOpening(float Alpha);
    void SealPassage();
    void UnsealPassage();
private:
    UPROPERTY() TObjectPtr<class UBoxComponent> PassageSeal;
    UPROPERTY() TObjectPtr<USceneComponent> LeftHinge;
    UPROPERTY() TObjectPtr<USceneComponent> RightHinge;
};
