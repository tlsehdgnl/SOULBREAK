#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SBImpact.generated.h"

class UInstancedStaticMeshComponent;
class UMaterialInterface;
class UPointLightComponent;
class UStaticMesh;
class UStaticMeshComponent;

UCLASS(NotBlueprintable)
class SOULBREAK_API ASBImpact : public AActor
{
    GENERATED_BODY()
public:
    ASBImpact();
    void Launch(UStaticMesh* Blade, const FVector& Velocity, float FloorZ, float Scale, FLinearColor Tint, float Size=1.f);
    virtual void Tick(float DeltaSeconds) override;
private:
    UPROPERTY() TObjectPtr<UStaticMeshComponent> Sword;
    UPROPERTY() TObjectPtr<UInstancedStaticMeshComponent> Sparks;
    UPROPERTY() TObjectPtr<UInstancedStaticMeshComponent> Fragments;
    UPROPERTY() TObjectPtr<UPointLightComponent> Flash;
    UPROPERTY() TObjectPtr<UMaterialInterface> LightMaterial;
    TArray<FVector> SparkVelocity;
    TArray<FVector> FragmentVelocity;
    FVector LaunchSpeed = FVector::ZeroVector;
    float Age = 0.f;
    float Ground = 0.f;
    float ShardSize = 1.f;
    float LandTime = 0.f;
    bool bFallenBlade = false;
};
