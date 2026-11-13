#include "Combat/SBTrainingDummy.h"
#include "Components/StaticMeshComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"
#include "UObject/ConstructorHelpers.h"

ASBTrainingDummy::ASBTrainingDummy()
{
    PrimaryActorTick.bCanEverTick = true;
    SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Stand")));
    Target = CreateDefaultSubobject<USceneComponent>(TEXT("Spring"));
    Target->SetupAttachment(RootComponent);
    Target->SetRelativeLocation(FVector(0,0,88));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> StandMesh(TEXT("/Game/SoulBreak/Armory/SM_PellStand"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> TargeMesh(TEXT("/Game/SoulBreak/Armory/SM_LeatherTarge"));
    auto* Stand = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Oak stand"));
    Stand->SetupAttachment(RootComponent);
    Stand->SetStaticMesh(StandMesh.Object);
    auto* Targe = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Lashed practice targe"));
    Targe->SetupAttachment(Target);
    Targe->SetStaticMesh(TargeMesh.Object);
    for (auto* Section : { Stand, Targe })
    {
        Section->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Section->SetCanEverAffectNavigation(false);
    }
    static ConstructorHelpers::FObjectFinderOptional<USoundBase> Cue(TEXT("/Game/SoulBreak/Audio/S_Impact"));
    Impact=Cue.Get();
}
bool ASBTrainingDummy::TraceSword(const FVector& From,const FVector& To) const
{
    if (Health<=0) return false;
    const FVector Base=GetActorLocation();
    FVector A,B;
    FMath::SegmentDistToSegmentSafe(From,To,Base+FVector(0,0,75),Base+FVector(0,0,171),A,B);
    return FVector::DistSquared(A,B) <= FMath::Square(39.f);
}
void ASBTrainingDummy::ApplySwordHit(int32 AttackId,float Damage)
{
    if (AttackId<=LastHitId || Damage<=0 || Health<=0) return;
    LastHitId=AttackId;
    Health=FMath::Max(0.f,Health-Damage);
    HitPulse=1.f; RestSeconds=0;
    if (Impact) UGameplayStatics::PlaySoundAtLocation(this,Impact,GetActorLocation(),.72f);
    UE_LOG(LogTemp,Display,TEXT("SoulBreak training hit %d, damage %.0f, remaining %.0f"),AttackId,Damage,Health);
}
void ASBTrainingDummy::Tick(float Dt)
{
    Super::Tick(Dt);
    HitPulse=FMath::Max(0.f,HitPulse-1.4f*Dt);
    RestSeconds+=Dt;
    if (RestSeconds>4) Health=100;
    Target->SetRelativeRotation(FRotator(0,0,HitPulse*FMath::Sin(RestSeconds*24.f)*16));
}
