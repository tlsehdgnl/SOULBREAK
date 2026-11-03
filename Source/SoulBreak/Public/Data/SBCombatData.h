#pragma once
#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "SBCombatData.generated.h"

class UAnimSequence;
class USoundBase;

UENUM(BlueprintType)
enum class ESBHeroAction : uint8 { Ready, Cut, ReturnCut, OathCut, Evade, Parry, Hurt, Dead };
UENUM(BlueprintType)
enum class ESBKnightAction : uint8 { Idle, Chase, SwordSweep, Bash, Stomp, Stagger, Transition, Dead };
UENUM() enum class ESBHitResult : uint8 { Miss, Body, Arm, Broken, Phase, Death };

USTRUCT(BlueprintType)
struct FSBAttackTiming
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float Cost = 15;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float Damage = 20;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float Duration = .6f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float Open = .18f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float Close = .32f;
    FSBAttackTiming() = default;
    FSBAttackTiming(float C, float D, float T, float A, float B) : Cost(C), Damage(D), Duration(T), Open(A), Close(B) {}
};

USTRUCT(BlueprintType)
struct FSBPattern
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float Range = 260;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float Angle = 100;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float Windup = .65f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float Active = .15f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float Recovery = .8f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float Damage = 22;
    FSBPattern() = default;
    FSBPattern(float R, float A, float W, float T, float C, float D) : Range(R), Angle(A), Windup(W), Active(T), Recovery(C), Damage(D) {}
    float Duration() const { return Windup + Active + Recovery; }
};

UCLASS(BlueprintType)
class SOULBREAK_API USBCombatData : public UDataAsset
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Presentation") TMap<FName,TObjectPtr<UAnimSequence>> Animations;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Presentation") TMap<FName,TObjectPtr<USoundBase>> Sounds;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FSBAttackTiming Cut;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FSBAttackTiming ReturnCut = FSBAttackTiming(20,30,.75f,.22f,.4f);
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FSBAttackTiming OathCut = FSBAttackTiming(0,40,.85f,.27f,.48f);
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FSBAttackTiming Evade = FSBAttackTiming(22,0,.48f,.08f,.30f);
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FSBAttackTiming Parry = FSBAttackTiming(15,0,.5f,.06f,.2f);
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FSBPattern Sweep;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FSBPattern Bash = FSBPattern(180,80,.45f,.12f,.7f,16);
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FSBPattern Stomp = FSBPattern(320,360,.9f,.15f,1.f,30);
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float RegenDelay = .7f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float RegenRate = 22;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float SprintCost = 12;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float StompCooldown = 4;
};

namespace SBCombat
{
    inline bool InWindow(float T, const FSBAttackTiming& W) { return T >= W.Open && T < W.Close; }
    inline bool Spend(float& Stamina, float Cost)
    {
        if (Stamina < Cost) return false;
        Stamina -= Cost;
        return true;
    }
    // A hit ID belongs to a single attack on this target. Resolve death before any phase/part event.
    inline ESBHitResult Resolve(int32 Id, int32& LastId, float Damage, bool bArm, float& Health, float& ArmHealth, bool& bBroken, int32& Phase)
    {
        if (Health <= 0 || Id <= LastId || Damage <= 0) return ESBHitResult::Miss;
        LastId = Id;
        Health = FMath::Max(0.f, Health - Damage);
        const bool bValidArm = bArm && !bBroken;
        if (bValidArm) ArmHealth = FMath::Max(0.f, ArmHealth - Damage);
        if (Health <= 0) return ESBHitResult::Death;
        if (bValidArm && ArmHealth <= 0) { bBroken = true; Phase = 2; return ESBHitResult::Broken; }
        if (Phase == 1 && Health <= 200) { Phase = 2; return ESBHitResult::Phase; }
        return bValidArm ? ESBHitResult::Arm : ESBHitResult::Body;
    }
}
