#pragma once
#include "Combat/SBFighter.h"
#include "SBKnight.generated.h"
class ASBHero;
class UBoxComponent;
class UCapsuleComponent;
class UInstancedStaticMeshComponent;
class UStaticMesh;
class UMaterialInstanceDynamic;

UCLASS()
class SOULBREAK_API ASBKnight : public ASBFighter
{
    GENERATED_BODY()
public:
    ASBKnight();
    UPROPERTY(BlueprintReadOnly) float ArmHealth = 90.f;
    UPROPERTY(BlueprintReadOnly) bool bArmBroken = false;
    UPROPERTY(BlueprintReadOnly) bool bEncounterActive = false;
    UPROPERTY(BlueprintReadOnly) int32 Phase = 1;
    UPROPERTY(BlueprintReadOnly) ESBKnightAction Action = ESBKnightAction::Idle;
    UPROPERTY(BlueprintReadOnly) FString PatternLabel;
    UPROPERTY(BlueprintReadOnly) float PatternElapsed = 0.f;
    UPROPERTY(BlueprintReadOnly) float TelegraphDuration = 0.f;
    UPROPERTY(BlueprintReadOnly) int32 AttackGeneration = 0;
    UPROPERTY(BlueprintReadOnly) int32 BreakCount = 0;
    UPROPERTY(BlueprintReadOnly) int32 PhaseChanges = 0;
    UPROPERTY(BlueprintReadOnly) int32 PatternsStarted = 0;
    UFUNCTION(BlueprintCallable) void StartEncounter(ASBHero* Target);
    UFUNCTION(BlueprintCallable) void StopEncounter();
    UFUNCTION(BlueprintCallable) void ApplySwordHit(int32 AttackId, float Damage, bool bHitArm);
    UFUNCTION(BlueprintCallable) void OnParried();
    void TraceSword(const FVector& From, const FVector& To, bool& bBody, bool& bArm) const;
    FVector ArmPoint() const;
    ASBHero* GetHero() const { return Hero; }
    void Think(float Dt);
    virtual void Tick(float Dt) override;
protected:
    virtual void BeginPlay() override;
private:
    UPROPERTY(VisibleAnywhere) TObjectPtr<UCapsuleComponent> Body;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UCapsuleComponent> Arm;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UInstancedStaticMeshComponent> Telegraph;
    UPROPERTY() TObjectPtr<ASBHero> Hero;
    UPROPERTY() TObjectPtr<UStaticMesh> FallenBlade;
    UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> RingMat;
    int32 LastHitId = -1;
    int32 NextPattern = 0;
    float NextStompTime = 0;
    float NextPathUpdate = 0;
    bool bPreferStomp = false;
    bool bImpactResolved = false;
    float BlackboardClock = 0.f;
    float StateDuration = 0.f;
    const FSBPattern* CurrentPattern() const;
    void Enter(ESBKnightAction State,float Duration);
    void StartPattern(ESBKnightAction Pattern);
    void SelectOrChase(float Dt);
    void BreakArm();
    void UpdateStompRing(float Progress);
    void StopMoving();
};
