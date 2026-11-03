#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SBReviewDriver.generated.h"

class ASBGameMode;
class ASBHero;
class ASBKnight;

// Development-only hands-free capture. GameMode never spawns this actor in a normal game.
UCLASS(NotBlueprintable)
class SOULBREAK_API ASBReviewDriver : public AActor
{
    GENERATED_BODY()
public:
    ASBReviewDriver();
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
private:
#if !UE_BUILD_SHIPPING && !UE_BUILD_TEST
    void Drive(ASBGameMode& Game, ASBHero& Hero, ASBKnight& Knight);
    void Measure(double Now, float WallFrameMs, ASBKnight& Knight);
    void Capture(const ASBGameMode& Game, const ASBHero& Hero, const ASBKnight& Knight);
    void Finish();
    FString OutputDirectory;
    TArray<float> FrameTimes;
    double PreviousFrame = 0;
    double SampleWindow = 0;
    int32 SampleIndex = 0;
    int32 LastPhase = 0;
    int32 LastParries = 0;
    int32 LastPatternGeneration = -1;
    int32 LastBossHP = 400;
    bool bLastBroken = false;
    bool bResultSeen = false;
    bool bPerf = false;
    bool bVideo = false;
    bool bFinishing = false;
#endif
};
