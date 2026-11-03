#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SBImpact.generated.h"
class UStaticMeshComponent;
class UInstancedStaticMeshComponent;
class UStaticMesh;
UCLASS(NotBlueprintable)
class SOULBREAK_API ASBImpact : public AActor
{
    GENERATED_BODY()
public:
    ASBImpact();
    void Launch(UStaticMesh* Blade,const FVector& Velocity,float FloorZ,float Scale,FLinearColor Tint,float Size=1.f);
    virtual void Tick(float Dt) override;
private:
    UPROPERTY() TObjectPtr<UStaticMeshComponent> Sword;
    UPROPERTY() TObjectPtr<UInstancedStaticMeshComponent> Chips;
    TArray<FVector> Speeds;
    FVector LaunchSpeed;
    float Age=0.f;
    float Ground=0.f;
    float ShardSize=1.f;
    bool bFallenBlade=false;
};
