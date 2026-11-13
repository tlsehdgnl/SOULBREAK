#include "Combat/SBMotionInstance.h"
#include "Animation/AnimSequence.h"
#include "Boss/SBKnight.h"
#include "Animation/AnimSingleNodeInstanceProxy.h"

namespace
{
// Cache the *displayed* pose. Interrupting a half-finished transition therefore starts
// exactly where the fighter is visible, including when a parry cancels a sword sweep.
class FSBFighterPoseProxy final : public FAnimSingleNodeInstanceProxy
{
public:
    explicit FSBFighterPoseProxy(UAnimInstance* Instance) : FAnimSingleNodeInstanceProxy(Instance) {}

    void BeginBlend(float Seconds)
    {
        Source = LastDisplayed;
        Duration = Seconds;
        Elapsed = 0.f;
    }

    virtual void PreUpdate(UAnimInstance* Instance, float Dt) override
    {
        FAnimSingleNodeInstanceProxy::PreUpdate(Instance, Dt);
        Elapsed += Dt;
        if (const auto* Fighter=Cast<ASBFighter>(Instance->GetOwningActor()); Fighter && Dt>SMALL_NUMBER)
        {
            const FVector Velocity=Fighter->GetVelocity();
            const float Yaw=Fighter->GetActorRotation().Yaw;
            if (bHasMotionSample)
            {
                const FVector Acceleration=Fighter->GetActorQuat().UnrotateVector((Velocity-LastVelocity)/Dt);
                const float TurnRate=FMath::FindDeltaAngleDegrees(LastYaw,Yaw)/Dt;
                const float Blend=1.f-FMath::Exp(-8.f*Dt);
                Lean=FMath::Lerp(Lean,FMath::Clamp(float(Acceleration.X)*.004f,-8.f,8.f),Blend);
                Bank=FMath::Lerp(Bank,FMath::Clamp(float(Acceleration.Y)*.003f,-6.f,6.f),Blend);
                ClothTurn=FMath::Lerp(ClothTurn,FMath::Clamp(-TurnRate*.045f,-19.f,19.f),Blend);
                ClothHem=FMath::Lerp(ClothHem,ClothTurn,1.f-FMath::Exp(-5.f*Dt));
            }
            bHasMotionSample=true;
            LastYaw=Yaw;
            LastVelocity=Velocity;
        }
        if (auto* K=Cast<ASBKnight>(Instance->GetOwningActor()))
        {
            Hop=K->HopPhase;
            OneLeg=K->bKneeBroken && K->Health>0;
            Recoil=K->bParryRecoil && !K->bArmBroken ? FMath::Clamp(K->PatternElapsed/.12f,0.f,1.f)*FMath::Clamp((1.5f-K->PatternElapsed)/.28f,0.f,1.f) : 0.f;
            Transition=K->Action==ESBKnightAction::Transition ? FMath::Sin(PI*FMath::Clamp(K->PatternElapsed,0.f,1.f)) : 0.f;
            ArmGone=K->bArmBroken;
        }
    }

    virtual bool Evaluate(FPoseContext& Output) override
    {
        FAnimSingleNodeInstanceProxy::Evaluate(Output);
        const int32 Count = Output.Pose.GetNumBones();
        if (Elapsed < Duration && Source.Num() == Count)
        {
            const float T = FMath::Clamp(Elapsed / Duration, 0.f, 1.f);
            const float Weight = T * T * (3.f - 2.f * T);
            for (const FCompactPoseBoneIndex Bone : Output.Pose.ForEachBoneIndex())
            {
                FTransform Blended;
                Blended.Blend(Source[Bone.GetInt()], Output.Pose[Bone], Weight);
                Output.Pose[Bone] = Blended;
            }
        }
        LastDisplayed.SetNumUninitialized(Count);
        for (const FCompactPoseBoneIndex Bone : Output.Pose.ForEachBoneIndex())
            LastDisplayed[Bone.GetInt()] = Output.Pose[Bone];
        auto Tilt=[&](FName Name, FVector Axis, float Degrees)
        {
            if (FMath::IsNearlyZero(Degrees)) return;
            const auto& Bones=Output.Pose.GetBoneContainer();
            const auto& Ref=Bones.GetReferenceSkeleton();
            int32 Index=Ref.FindBoneIndex(Name);
            if (Index==INDEX_NONE) return;
            auto Compact=Bones.MakeCompactPoseIndex(FMeshPoseBoneIndex(Index));
            if (!Compact.IsValid()) return;
            FQuat Basis=Ref.GetRefBonePose()[Index].GetRotation();
            while ((Index=Ref.GetParentIndex(Index))!=INDEX_NONE) Basis=Ref.GetRefBonePose()[Index].GetRotation()*Basis;
            Output.Pose[Compact].ConcatenateRotation(FQuat(Basis.UnrotateVector(Axis),FMath::DegreesToRadians(Degrees)));
            Output.Pose[Compact].NormalizeRotation();
        };
        Tilt(TEXT("Chest"),FVector::ForwardVector,-Lean);
        Tilt(TEXT("Chest"),FVector::RightVector,-Bank);
        Tilt(TEXT("Head"),FVector::ForwardVector,Lean*.52f);
        Tilt(TEXT("CloakMid"),FVector::UpVector,ClothTurn*.45f);
        Tilt(TEXT("CloakHem"),FVector::UpVector,ClothHem*.65f);
        if (OneLeg)
        {
            const float Air=FMath::Sin(PI*Hop);
            Tilt(TEXT("ThighL"),FVector::ForwardVector,-33);
            Tilt(TEXT("ThighR"),FVector::ForwardVector,-18*Air);
            Tilt(TEXT("ShinR"),FVector::ForwardVector,35*Air);
            Tilt(TEXT("Chest"),FVector::RightVector,7+4*Air);
        }
        Tilt(TEXT("UpperArmR"),FVector::RightVector,46*Recoil);
        Tilt(TEXT("ForearmR"),FVector::ForwardVector,-16*Recoil);
        Tilt(TEXT("Chest"),FVector::UpVector,ArmGone ? -18*Transition : 12*Transition);
        if (ArmGone)
        {
            Tilt(TEXT("Chest"),FVector::RightVector,18*Transition);
            Tilt(TEXT("UpperArmL"),FVector::ForwardVector,-35*Transition);
        }
        else Tilt(TEXT("ForearmR"),FVector::ForwardVector,32*Transition);
        if (Transition>.001f && !ArmGone)
        {
            auto Joint=[&](FName Name) {
                return Output.Pose.GetBoneContainer().MakeCompactPoseIndex(FMeshPoseBoneIndex(
                    Output.Pose.GetBoneContainer().GetReferenceSkeleton().FindBoneIndex(Name)));
            };
            const auto Hand=Joint(TEXT("HandR")), Tip=Joint(TEXT("BladeTip"));
            if (Hand.IsValid() && Tip.IsValid())
            {
                FCSPose<FCompactPose> ComponentPose;
                ComponentPose.InitPose(Output.Pose);
                const FTransform Wrist=ComponentPose.GetComponentSpaceTransform(Hand);
                const FVector Blade=ComponentPose.GetComponentSpaceTransform(Tip).GetLocation()-Wrist.GetLocation();
                const FVector Drag=FVector(-.23,-.21,-1.).GetSafeNormal();
                const FQuat Turn=FQuat::FindBetweenNormals(Blade.GetSafeNormal(),Drag);
                const FQuat LocalTurn=Wrist.GetRotation().Inverse()*Turn*Wrist.GetRotation();
                Output.Pose[Hand].ConcatenateRotation(FQuat::Slerp(FQuat::Identity,LocalTurn,Transition));
                Output.Pose[Hand].NormalizeRotation();
            }
        }
        return true;
    }

private:
    FVector LastVelocity=FVector::ZeroVector;
    float LastYaw=0, Lean=0, Bank=0, ClothTurn=0, ClothHem=0;
    bool bHasMotionSample=false;
    TArray<FTransform> LastDisplayed;
    TArray<FTransform> Source;
    float Hop=0, Recoil=0, Transition=0;
    bool OneLeg=false, ArmGone=false;
    float Elapsed = 0;
    float Duration = 0;
};
}

FAnimInstanceProxy* USBMotionInstance::CreateAnimInstanceProxy()
{
    return new FSBFighterPoseProxy(this);
}

void USBMotionInstance::PlayClip(UAnimSequence* Clip, bool bLoop, float Rate, float BlendSeconds, bool bMatchGait)
{
    if (!Clip) return;
    const float OldLength = GetLength();
    const float StridePhase = bMatchGait && OldLength > 0.f ? GetCurrentTime() / OldLength : 0.f;
    GetProxyOnGameThread<FSBFighterPoseProxy>().BeginBlend(BlendSeconds);
    SetAnimationAsset(Clip, bLoop, Rate);
    if (bMatchGait) SetPosition(FMath::Fmod(StridePhase, 1.f) * Clip->GetPlayLength(), false);
    SetPlaying(true);
}
