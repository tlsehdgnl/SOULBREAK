#include "Combat/SBBladeTrailComponent.h"
#include "Player/SBHero.h"
#include "Boss/SBKnight.h"
#include "Components/SkeletalMeshComponent.h"
#include "Materials/MaterialInterface.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
constexpr int32 Rows = 14;
constexpr int32 Columns = 4;
constexpr float Lifetime = .095f;
const float AcrossBlade[Columns] = {.30f,.79f,.975f,1.f};
const float Opacity[Columns] = {0.f,.11f,.58f,.02f};
}
USBBladeTrailComponent::USBBladeTrailComponent(const FObjectInitializer& Initializer) : Super(Initializer)
{
    PrimaryComponentTick.bCanEverTick = true;
    PrimaryComponentTick.TickGroup = TG_PostPhysics;
    SetCollisionEnabled(ECollisionEnabled::NoCollision);
    SetGenerateOverlapEvents(false);
    SetCastShadow(false);
    SetCanEverAffectNavigation(false);
    SetVisibility(false);
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Material(TEXT("/Game/SoulBreak/FX/M_BladeLight"));
    if (Material.Succeeded()) SetMaterial(0,Material.Object);
}
void USBBladeTrailComponent::BeginPlay()
{
    Super::BeginPlay();
    Hero = Cast<ASBHero>(GetOwner());
    Knight = Cast<ASBKnight>(GetOwner());
    const ACharacter* Fighter = Hero ? static_cast<ACharacter*>(Hero.Get()) : static_cast<ACharacter*>(Knight.Get());
    if (!Fighter || GetNetMode()==NM_DedicatedServer)
    {
        SetComponentTickEnabled(false);
        return;
    }
    Rig = Fighter->GetMesh();
    AddTickPrerequisiteComponent(Rig);
    History.Reserve(Rows);
    Vertices.SetNumZeroed(Rows*Columns);
    Colors.Init(FLinearColor::Transparent, Rows*Columns);
    TArray<int32> Indices;
    for (int32 Row=0; Row<Rows-1; ++Row)
    {
        for (int32 Column=0; Column<Columns-1; ++Column)
        {
            int32 A=Row*Columns+Column, B=A+Columns;
            Indices.Append({A,B,A+1,A+1,B,B+1});
        }
    }
    CreateMeshSection_LinearColor(0,Vertices,Indices,{},{},Colors,{},false,false);
}
USBBladeTrailComponent::EStroke USBBladeTrailComponent::CurrentStroke() const
{
    if (Hero && Hero->CombatData)
    {
        const FSBAttackTiming* Window = nullptr;
        EStroke Stroke = EStroke::None;
        switch (Hero->Action)
        {
        case ESBHeroAction::Cut: Window=&Hero->CombatData->Cut; Stroke=EStroke::Cut; break;
        case ESBHeroAction::ReturnCut: Window=&Hero->CombatData->ReturnCut; Stroke=EStroke::Return; break;
        case ESBHeroAction::OathCut: Window=&Hero->CombatData->OathCut; Stroke=EStroke::Oath; break;
        default: break;
        }
        if (Window && Hero->ActionElapsed >= Window->Open-.06f && Hero->ActionElapsed <= Window->Close+.035f) return Stroke;
    }
    if (Knight && Knight->CombatData && !Knight->bArmBroken && Knight->Action==ESBKnightAction::SwordSweep)
    {
        const FSBPattern& P = Knight->CombatData->Sweep;
        if (Knight->PatternElapsed >= P.Windup-.09f && Knight->PatternElapsed <= P.Windup+P.Active+.04f) return EStroke::Knight;
    }
    return EStroke::None;
}
void USBBladeTrailComponent::TickComponent(float Dt,ELevelTick TickType,FActorComponentTickFunction* TickFunction)
{
    Super::TickComponent(Dt,TickType,TickFunction);
    const double Now = GetWorld()->GetTimeSeconds();
    if (Knight && Knight->bArmBroken) History.Reset();
    while (History.Num() && Now-History[0].Time>Lifetime)
        History.RemoveAt(0,1,EAllowShrinking::No);
    const EStroke Stroke=CurrentStroke();
    if (Stroke!=EStroke::None && Rig && Rig->DoesSocketExist(TEXT("BladeTip")))
    {
        FSample Sample{Rig->GetSocketLocation(TEXT("BladeBase")),Rig->GetSocketLocation(TEXT("BladeTip")),Now};
        if (Stroke!=LastStroke || (History.Num() && FVector::DistSquared(History.Last().Tip,Sample.Tip)>FMath::Square(180.f)))
            History.Reset();
        LastStroke=Stroke;
        if (History.IsEmpty() || FVector::DistSquared(History.Last().Tip,Sample.Tip)>1.f)
        {
            if (History.Num()==Rows) History.RemoveAt(0,1,EAllowShrinking::No);
            History.Add(Sample);
        }
    }
    const bool bVisible = History.Num()>=2;
    if (bVisible!=bVisibleLastFrame) SetVisibility(bVisible);
    bVisibleLastFrame=bVisible;
    if (bVisible) DrawHistory(Now);
}
void USBBladeTrailComponent::DrawHistory(double Now)
{
    const FLinearColor Ink = LastStroke==EStroke::Knight ? FLinearColor(.98f,.34f,.075f)
        : LastStroke==EStroke::Oath ? FLinearColor(.09f,1.f,.77f) : FLinearColor(.45f,.67f,.8f);
    for (int32 Row=0; Row<Rows; ++Row)
    {
        const FSample& S = History[FMath::Min(Row,History.Num()-1)];
        const float Freshness = FMath::Clamp(1.f-static_cast<float>((Now-S.Time)/Lifetime),0.f,1.f);
        for (int32 Column=0; Column<Columns; ++Column)
        {
            const int32 Index = Row*Columns+Column;
            Vertices[Index]=GetComponentTransform().InverseTransformPosition(FMath::Lerp(S.Base,S.Tip,AcrossBlade[Column]));
            Colors[Index]=FMath::Lerp(Ink,FLinearColor::White,Column==2 ? .40f*Freshness : 0.f);
            Colors[Index].A=Opacity[Column]*Freshness*Freshness*(LastStroke==EStroke::Oath ? 1.45f : .8f);
        }
    }
    UpdateMeshSection_LinearColor(0,Vertices,{},{},Colors,{},false);
}
