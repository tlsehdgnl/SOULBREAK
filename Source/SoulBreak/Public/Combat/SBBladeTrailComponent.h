#pragma once
#include "CoreMinimal.h"
#include "ProceduralMeshComponent.h"
#include "SBBladeTrailComponent.generated.h"

class USkeletalMeshComponent;
class ASBHero;
class ASBKnight;

// A short exposure of the real blade sockets. It never drives damage or attack timing.
UCLASS()
class SOULBREAK_API USBBladeTrailComponent : public UProceduralMeshComponent
{
    GENERATED_BODY()
public:
    USBBladeTrailComponent(const FObjectInitializer& Initializer);
    virtual void BeginPlay() override;
    virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* TickFunction) override;
private:
    struct FSample { FVector Base, Tip; double Time; };
    enum class EStroke : uint8 { None, Cut, Return, Oath, Knight };
    EStroke CurrentStroke() const;
    void DrawHistory(double Now);
    UPROPERTY() TObjectPtr<ASBHero> Hero;
    UPROPERTY() TObjectPtr<ASBKnight> Knight;
    UPROPERTY() TObjectPtr<USkeletalMeshComponent> Rig;
    TArray<FSample> History;
    TArray<FVector> Vertices;
    TArray<FLinearColor> Colors;
    EStroke LastStroke = EStroke::None;
    bool bVisibleLastFrame = false;
};
