#include "Combat/SBCombatComponent.h"
#include "Player/SBHero.h"
#include "Boss/SBKnight.h"
#include "Combat/SBTrainingDummy.h"

void USBCombatComponent::StartCut() { ++AttackId; bBodyPending=false; bResolved=false; }
void USBCombatComponent::Cancel() { bBodyPending=false; bResolved=true; }
void USBCombatComponent::TraceCut(ASBHero& Hero,ASBKnight* Knight,ASBTrainingDummy* Dummy,const FSBAttackTiming& W,bool bReverse,float Previous,float Now)
{
    if (bResolved || Now<W.Open || Previous>=W.Close) return;
    bool bBoss=IsValid(Knight) && Knight->bEncounterActive;
    if (!bBoss && (!IsValid(Dummy) || (IsValid(Knight) && Knight->Health<=0))) return;
    float A = FMath::Clamp((Previous-W.Open)/(W.Close-W.Open),0.f,1.f);
    float B = FMath::Clamp((Now-W.Open)/(W.Close-W.Open),0.f,1.f);
    const int32 Segments = FMath::Max(1,FMath::CeilToInt((B-A)*12));
    const FVector Origin = Hero.GetActorLocation()+FVector(0,0,22);
    auto Point = [&](float T,float R) {
        const float U = bReverse ? 1-T:T;
        FVector Dir = Hero.GetActorForwardVector().RotateAngleAxis(FMath::Lerp(64.f,-64.f,U),FVector::UpVector);
        return Origin+Dir*R+FVector(0,0,(.2f+.25f*(1-U))*R);
    };
    bool bArm=false;
    for (int32 I=0; I<Segments && !bArm; ++I)
    {
        const float From=FMath::Lerp(A,B,float(I)/Segments),To=FMath::Lerp(A,B,float(I+1)/Segments);
        for(float R : {36.f,56.f,76.f,96.f,116.f,132.f})
        {
            if (bBoss) Knight->TraceSword(Point(From,R),Point(To,R),bBodyPending,bArm);
            else if (!bBodyPending) bBodyPending=Dummy->TraceSword(Point(From,R),Point(To,R));
        }
    }
    if (bArm || (Now>=W.Close && bBodyPending))
    {
        bResolved=true;
        if (bBoss) Knight->ApplySwordHit(AttackId,W.Damage,bArm);
        else Dummy->ApplySwordHit(AttackId,W.Damage);
        Hero.ImpactCamera(bArm ? .34f : .22f);
    }
}
