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
    UPROPERTY(BlueprintReadOnly) float ShieldHealth = 75.f;
    UPROPERTY(BlueprintReadOnly) float KneeHealth = 65.f;
    UPROPERTY(BlueprintReadOnly) bool bShieldBroken = false;
    UPROPERTY(BlueprintReadOnly) bool bKneeBroken = false;
    UPROPERTY(BlueprintReadOnly) ESBArmorPart LastBrokenPart = ESBArmorPart::Body;
    UPROPERTY(BlueprintReadOnly) bool bEncounterActive = false;
    UPROPERTY(BlueprintReadOnly) int32 Phase = 1;
    UPROPERTY(BlueprintReadOnly) ESBKnightAction Action = ESBKnightAction::Idle;
    UPROPERTY(BlueprintReadOnly) FString PatternLabel;
    UPROPERTY(BlueprintReadOnly) float PatternElapsed = 0.f;
    UPROPERTY(BlueprintReadOnly) float TelegraphDuration = 0.f;
    UPROPERTY(BlueprintReadOnly) float HitFeedbackRemaining = 0.f;
    UPROPERTY(BlueprintReadOnly) ESBArmorPart LastHitPart = ESBArmorPart::Body;
    UPROPERTY(BlueprintReadOnly) int32 AttackGeneration = 0;
    UPROPERTY(BlueprintReadOnly) int32 BreakCount = 0;
    UPROPERTY(BlueprintReadOnly) int32 PhaseChanges = 0;
    UPROPERTY(BlueprintReadOnly) int32 PatternsStarted = 0;
    UFUNCTION(BlueprintCallable) void StartEncounter(ASBHero* Target);
    UFUNCTION(BlueprintCallable) void StopEncounter();
    UFUNCTION(BlueprintCallable) void ApplySwordHit(int32 AttackId, float Damage, bool bHitArm);
    UFUNCTION(BlueprintCallable) void ApplyPartHit(int32 AttackId, float Damage, ESBArmorPart Part);
    UFUNCTION(BlueprintPure) float GetPartHealth(ESBArmorPart Part) const;
    UFUNCTION(BlueprintPure) float GetPartMaxHealth(ESBArmorPart Part) const;
    UFUNCTION(BlueprintPure) bool IsPartBroken(ESBArmorPart Part) const;
    UFUNCTION(BlueprintPure) FVector PartPoint(ESBArmorPart Part) const;
    UFUNCTION(BlueprintPure) bool IsPunishWindow() const;
    UFUNCTION(BlueprintPure) bool IsRecoveryWindow() const;
    UFUNCTION(BlueprintCallable) void OnParried();
    bool TracePart(const FVector& From,const FVector& To,ESBArmorPart Part,bool bAimed=false) const;
    FVector ArmPoint() const;
    ASBHero* GetHero() const { return Hero; }
    bool bParryRecoil = false;
    bool bOathFinish = false;
    float HopPhase = 0.f;
    void Think(float Dt);
    void RaiseGuard();
    void RoarPose();
    virtual void Tick(float Dt) override;
protected:
    virtual void BeginPlay() override;
private:
    UPROPERTY(VisibleAnywhere) TObjectPtr<UCapsuleComponent> Body;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UCapsuleComponent> Arm;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UCapsuleComponent> Shield;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UCapsuleComponent> Knee;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UInstancedStaticMeshComponent> Telegraph;
    UPROPERTY() TObjectPtr<ASBHero> Hero;
    UPROPERTY() TObjectPtr<UStaticMesh> FallenBlade;
    UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> RingMat;
    float MeshRestZ = 0.f;
    UPROPERTY() TArray<TObjectPtr<class UStaticMeshComponent>> Fractures;
    void CreateFractures();
    void UpdateFractures(ESBArmorPart Part);
    int32 LastHitId = -1;
    int32 NextPattern = 0;
    float NextStompTime = 0;
    double NextWaveTime = 0;
    double NextChargeTime = 0;
    float NextPathUpdate = 0;
    bool bPreferStomp = false;
    bool bImpactResolved = false;
    bool bChargeBlocked = false;
    bool bChargeConnected = false;
    FVector ChargeForward = FVector::ForwardVector;
    float ChargeDistance = 0;
    double PreviousWaveDistance = 0;
    float BlackboardClock = 0.f;
    float StateDuration = 0.f;
    const FSBPattern* CurrentPattern() const;
    void Enter(ESBKnightAction State,float Duration);
    void StartPattern(ESBKnightAction Pattern);
    void SelectOrChase(float Dt);
    UCapsuleComponent* PartCollider(ESBArmorPart Part) const;
    void BreakPart(ESBArmorPart Part);
    void UpdateRing(float OuterRadius,float InnerRadius);
    void UpdateChargeLane();
    void TickCharge(const FSBPattern& Pattern,float Previous);
    void TickWave(const FSBPattern& Pattern,float Previous);
    void StopMoving();
    bool HasClearContact() const;
};
