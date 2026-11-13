#include "Combat/SBCombatComponent.h"
#include "Player/SBHero.h"
#include "Boss/SBKnight.h"
#include "Combat/SBTrainingDummy.h"

void USBCombatComponent::StartCut(bool bLocked,ESBArmorPart Part)
{
    ++AttackId; bBodyPending=false; bResolved=false; bTargeted=bLocked; SelectedPart=Part;
    FreeContact=ESBArmorPart::Body;
}
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
    FCollisionQueryParams OcclusionQuery(SCENE_QUERY_STAT(PlayerSwordContact),false,&Hero);
    if (bBoss) OcclusionQuery.AddIgnoredActor(Knight);
    const bool bRack=!bBoss && Hero.UsesRack();
    const bool bAimPart=(bBoss || bRack) && bTargeted && SelectedPart!=ESBArmorPart::Body && !Knight->IsPartBroken(SelectedPart);
    const FVector Aim=bAimPart ? Hero.TargetPoint(SelectedPart)-Origin : FVector::ZeroVector;
    const FVector TowardHero=bBoss ? (Origin-Knight->GetActorLocation()).GetSafeNormal2D() : FVector::ZeroVector;
    const bool bAtFlank=bBoss && FMath::Abs(FVector::DotProduct(TowardHero,Knight->GetActorForwardVector()))<.6;
    // At point-blank range the shoulder or knee may be almost directly above/below the grip.
    const double GripLift=bAimPart ? FMath::Clamp(Aim.Z,-35.,35.) * (1.-FMath::Clamp(Aim.Size2D()/75.,0.,1.)) : 0.;
    auto Point = [&](float T,float R) {
        const float U = bReverse ? 1-T:T;
        FVector Dir = Hero.GetActorForwardVector().RotateAngleAxis(FMath::Lerp(64.f,-64.f,U),FVector::UpVector);
        const double Rise=bAimPart ? GripLift+FMath::Clamp((Aim.Z-GripLift)/FMath::Max(12.,Aim.Size2D()),-1.75,1.75)*R : (.2f+.25f*(1-U))*R;
        return Origin+Dir*R+FVector(0,0,Rise);
    };
    ESBArmorPart HitPart=ESBArmorPart::Body;
    for (int32 I=0; I<Segments && HitPart==ESBArmorPart::Body; ++I)
    {
        const float From=FMath::Lerp(A,B,float(I)/Segments),To=FMath::Lerp(A,B,float(I+1)/Segments);
        for(float R : {12.f,24.f,36.f,56.f,76.f,96.f,116.f,132.f})
        {
            const FVector Start=Point(From,R), End=Point(To,R);
            FHitResult Obstruction;
            if (Hero.GetWorld()->LineTraceSingleByObjectType(Obstruction,Origin,End,
                FCollisionObjectQueryParams(ECC_WorldStatic),OcclusionQuery)) continue;
            if (bBoss)
            {
                for (ESBArmorPart Part : {ESBArmorPart::SwordArm,ESBArmorPart::Shield,ESBArmorPart::Knee})
                {
                    if ((!bTargeted || Part==SelectedPart) && Knight->TracePart(Start,End,Part,bAimPart))
                    {
                        if (bTargeted) HitPart=Part;
                        else if (bAtFlank && FVector::DotProduct(Knight->PartPoint(Part)-Knight->PartPoint(ESBArmorPart::Body),TowardHero)>12.)
                            HitPart=Part;
                        else if (FreeContact==ESBArmorPart::Body) FreeContact=Part;
                        break;
                    }
                }
                if (HitPart!=ESBArmorPart::Body) break;
                if (!bBodyPending) bBodyPending=Knight->TracePart(Start,End,ESBArmorPart::Body);
            }
            else
            {
                if (bRack)
                {
                    for (ESBArmorPart Part : {ESBArmorPart::SwordArm,ESBArmorPart::Shield,ESBArmorPart::Knee})
                        if ((!bTargeted || Part==SelectedPart) && Dummy->TraceRack(Start,End,Part,bAimPart))
                        { HitPart=Part; break; }
                    if (HitPart!=ESBArmorPart::Body) break;
                }
                if (!bBodyPending) bBodyPending=Dummy->TraceSword(Start,End);
            }
        }
    }
    if (!bTargeted && Now>=W.Close && !bBodyPending) HitPart=FreeContact;
    if (HitPart!=ESBArmorPart::Body || (Now>=W.Close && bBodyPending))
    {
        bResolved=true;
        if (bBoss) Knight->ApplyPartHit(AttackId,W.Damage,HitPart);
        else if (HitPart!=ESBArmorPart::Body) Dummy->HitRack(HitPart,AttackId);
        else Dummy->ApplySwordHit(AttackId,W.Damage);
        Hero.ImpactCamera(HitPart!=ESBArmorPart::Body ? .34f : .22f);
    }
}
