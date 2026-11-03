#include "Combat/SBMotionInstance.h"
#include "Animation/AnimSequence.h"
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
        return true;
    }

private:
    TArray<FTransform> LastDisplayed;
    TArray<FTransform> Source;
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
