#pragma once
#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "SBCombatData.generated.h"

class UAnimSequence;
class USoundBase;

UENUM(BlueprintType)
enum class ESBHeroAction : uint8 { Ready, Cut, ReturnCut, OathCut, Evade, Parry, Hurt, Dead };
UENUM(BlueprintType)
enum class ESBKnightAction : uint8 { Idle, Chase, SwordSweep, Bash, Stomp, Stagger, Transition, Dead, ShieldCharge, BellWave, ShoulderCheck, Challenge, ShieldRecoil };
UENUM(BlueprintType)
enum class ESBArmorPart : uint8 { Body, SwordArm, Shield, Knee };
UENUM() enum class ESBHitResult : uint8 { Miss, Body, Arm, Broken, Phase, Death, Plate };

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
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FSBPattern ShieldCharge = FSBPattern(670,0,.76f,.48f,1.15f,28);
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FSBPattern BellWave = FSBPattern(535,360,.95f,.72f,.65f,24);
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FSBPattern ShoulderCheck = FSBPattern(155,95,.38f,.12f,.56f,14);
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float ShieldDurability = 75;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float KneeDurability = 65;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float RegenDelay = .7f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float RegenRate = 22;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float SprintCost = 12;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float StompCooldown = 4;
};

namespace SBCombat
{
    inline float RecoveryDuration(ESBKnightAction Action,float AuthoredRecovery)
    {
        const float Minimum=Action==ESBKnightAction::ShieldCharge ? 1.5f :
            Action==ESBKnightAction::Stomp ? 1.45f : Action==ESBKnightAction::BellWave ? 1.4f : .6f;
        return FMath::Max(AuthoredRecovery,Minimum);
    }
    // Match authored anticipation, contact and recovery to the gameplay clock independently.
    inline float AttackPoseTime(float Elapsed, float Open, float Close, float Duration, float Contact, float FollowThrough)
    {
        if (Elapsed<Open) return Contact*FMath::Clamp(Elapsed/FMath::Max(Open,KINDA_SMALL_NUMBER),0.f,1.f);
        if (Elapsed<Close) return FMath::Lerp(Contact,FollowThrough,FMath::Clamp((Elapsed-Open)/FMath::Max(Close-Open,KINDA_SMALL_NUMBER),0.f,1.f));
        return FMath::Lerp(FollowThrough,1.f,FMath::Clamp((Elapsed-Close)/FMath::Max(Duration-Close,KINDA_SMALL_NUMBER),0.f,1.f));
    }
    inline bool CanParry(ESBKnightAction Action)
    {
        return Action==ESBKnightAction::SwordSweep || Action==ESBKnightAction::Bash ||
            Action==ESBKnightAction::ShieldCharge || Action==ESBKnightAction::ShoulderCheck;
    }
    inline bool InWindow(float T, const FSBAttackTiming& W) { return T >= W.Open && T < W.Close; }
    inline bool Spend(float& Stamina, float Cost)
    {
        if (Stamina < Cost) return false;
        Stamina -= Cost;
        return true;
    }
    // A hit ID belongs to a single attack on this target. Resolve death before any phase/part event.
    inline ESBHitResult ResolvePart(int32 Id, int32& LastId, float Damage, ESBArmorPart Part, float& Health, float& Durability, bool& bBroken, int32& Phase, float PartScale = 1.f)
    {
        if (Health <= 0 || Id <= LastId || Damage <= 0) return ESBHitResult::Miss;
        LastId = Id;
        Health = FMath::Max(0.f, Health - Damage);
        const bool bValidPart = Part != ESBArmorPart::Body && !bBroken;
        if (bValidPart) Durability = FMath::Max(0.f, Durability - Damage * PartScale);
        if (Health <= 0) return ESBHitResult::Death;
        const bool bBreak = bValidPart && Durability <= 0;
        if (bBreak) bBroken = true;
        const bool bEnterPhase = Phase == 1 && (Health <= 200 || (bBreak && Part == ESBArmorPart::SwordArm));
        if (bEnterPhase) Phase = 2;
        if (bBreak) return ESBHitResult::Broken;
        if (bEnterPhase) return ESBHitResult::Phase;
        if (!bValidPart) return ESBHitResult::Body;
        return Part==ESBArmorPart::SwordArm ? ESBHitResult::Arm : ESBHitResult::Plate;
    }
    inline ESBHitResult Resolve(int32 Id, int32& LastId, float Damage, bool bArm, float& Health, float& ArmHealth, bool& bBroken, int32& Phase)
    {
        return ResolvePart(Id,LastId,Damage,bArm ? ESBArmorPart::SwordArm : ESBArmorPart::Body,Health,ArmHealth,bBroken,Phase);
    }
}
