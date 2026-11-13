#pragma once
#include "GameFramework/Actor.h"
#include "SBGroundDust.generated.h"

class UInstancedStaticMeshComponent;

// Short, non-colliding flagstone dust kicked up by heavy footwork.
UCLASS(NotBlueprintable)
class SOULBREAK_API ASBGroundDust : public AActor
{
    GENERATED_BODY()
public:
    ASBGroundDust();
    static void Kick(UWorld* World,const FVector& Floor,const FVector& Travel,float Radius);
    virtual void Tick(float DeltaSeconds) override;
private:
    UPROPERTY() TObjectPtr<UInstancedStaticMeshComponent> Clouds;
    FVector Direction=FVector::ZeroVector;
    float Reach=100.f;
    float Age=0.f;
};
