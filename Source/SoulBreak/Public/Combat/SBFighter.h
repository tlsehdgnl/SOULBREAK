#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "Data/SBCombatData.h"
#include "SBFighter.generated.h"

class UAnimSequence;
class USoundBase;

UCLASS(Abstract)
class SOULBREAK_API ASBFighter : public ACharacter
{
    GENERATED_BODY()
public:
    ASBFighter();
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="Combat") TObjectPtr<USBCombatData> CombatData;
    UPROPERTY(BlueprintReadOnly, Category="Combat") float Health = 100.f;
    UPROPERTY(BlueprintReadOnly, Category="Combat") float HitPulse = 0.f;
    virtual void Tick(float DeltaSeconds) override;
protected:
    void LoadFighter(const FString& Name, float DesiredHeight);
    void Pose(FName Clip, bool bLoop = false, float Duration = 0.f, bool bRestart = false);
    void PlayCue(FName Name, float Volume = 1.f, float Pitch = 1.f);
    void Locomotion(float WalkSpeed);
    void Face(const FVector& Direction, float MaxDegrees);
    void AlignMesh(float DesiredHeight);
    virtual void BeginPlay() override;
private:
    UPROPERTY(Transient) TMap<FName,TObjectPtr<UAnimSequence>> Clips;
    UPROPERTY(Transient) TMap<FName,TObjectPtr<USoundBase>> Cues;
    FName CurrentClip;
    bool bHeavy = false;
    float NextStep = 0.f;
};
