#pragma once

#include "Animation/AnimSingleNodeInstance.h"
#include "SBMotionInstance.generated.h"

class UAnimSequence;

// Keep Unreal's native sequence player, so notifies and action timing run on the incoming clip.
UCLASS(Transient, NotBlueprintable)
class SOULBREAK_API USBMotionInstance : public UAnimSingleNodeInstance
{
    GENERATED_BODY()
public:
    void PlayClip(UAnimSequence* Clip, bool bLoop, float Rate, float BlendSeconds, bool bMatchGait);
protected:
    virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override;
};
