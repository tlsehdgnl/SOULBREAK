#pragma once
#include "Combat/SBFighter.h"
#include "SBHero.generated.h"
class ASBKnight;
class ASBTrainingDummy;
class UCameraComponent;
class USpringArmComponent;
class UInputAction;
class UInputMappingContext;
class UEnhancedInputLocalPlayerSubsystem;
class USBCombatComponent;
struct FInputActionValue;

UCLASS()
class SOULBREAK_API ASBHero : public ASBFighter
{
    GENERATED_BODY()
public:
    ASBHero();
    UPROPERTY(BlueprintReadOnly) float Stamina = 100.f;
    UPROPERTY(BlueprintReadOnly) bool bLockedOn = false;
    UPROPERTY(BlueprintReadOnly) ESBHeroAction Action = ESBHeroAction::Ready;
    UPROPERTY(BlueprintReadOnly) float ActionElapsed = 0.f;
    UPROPERTY(BlueprintReadOnly) float ParryPulse = 0.f;
    UPROPERTY(BlueprintReadOnly) int32 SuccessfulParries = 0;
    UPROPERTY(BlueprintReadOnly) int32 DodgedHits = 0;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) TObjectPtr<USBCombatComponent> Combat;
    UFUNCTION(BlueprintCallable) void SetKnight(ASBKnight* NewKnight);
    UPROPERTY(BlueprintReadOnly) bool bOathReady = false;
    UFUNCTION(BlueprintCallable) void SetDummy(ASBTrainingDummy* Dummy);
    UFUNCTION(BlueprintCallable) void TryOathCut();
    UFUNCTION(BlueprintCallable) void TryAttack();
    UFUNCTION(BlueprintCallable) void TryDodge();
    UFUNCTION(BlueprintCallable) void TryParry();
    UFUNCTION(BlueprintCallable) void ToggleLock();
    UFUNCTION(BlueprintCallable) void SetMoveStick(FVector2D RightForward);
    UFUNCTION(BlueprintCallable) void SetSprinting(bool bHeld);
    UFUNCTION(BlueprintCallable) void ReceivePattern(float Damage, bool bSword);
    void ImpactCamera(float Strength);
    virtual void PawnClientRestart() override;
    virtual void Tick(float Dt) override;
    virtual void SetupPlayerInputComponent(UInputComponent* Input) override;
protected:
    virtual void BeginPlay() override;
    virtual void UnPossessed() override;
    virtual void EndPlay(EEndPlayReason::Type Why) override;
private:
    UPROPERTY(VisibleAnywhere) TObjectPtr<USpringArmComponent> Boom;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UCameraComponent> Camera;
    UPROPERTY() TObjectPtr<ASBKnight> Knight;
    UPROPERTY() TObjectPtr<ASBTrainingDummy> Dummy;
    UPROPERTY() TObjectPtr<UInputMappingContext> Mapping;
    TWeakObjectPtr<UEnhancedInputLocalPlayerSubsystem> MappingOwner;
    void RemoveMapping();
    UPROPERTY() TObjectPtr<UInputAction> MoveAction;
    UPROPERTY() TObjectPtr<UInputAction> LookAction;
    FVector2D Stick = FVector2D::ZeroVector;
    FVector DodgeDirection = FVector::ForwardVector;
    float SpentAt = -10.f;
    float Shake = 0.f;
    double AcceptLookAfter = 0;
    bool bHasMouseSample = false;
    bool bSprintHeld = false;
    bool bQueuedCombo = false;
    bool bNeedsSprintRecovery = false;
    FVector WishDirection() const;
    void MoveInput(const FInputActionValue& Value);
    void LookInput(const FInputActionValue& Value);
    void BeginAction(ESBHeroAction Next, FName Clip, float Duration);
    void BeginCut(bool bSecond);
    bool Spend(float Cost);
    void UpdateCamera(float Dt);
};
