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
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cylinder(TEXT("/Engine/BasicShapes/Cylinder"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Sphere(TEXT("/Engine/BasicShapes/Sphere"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Box(TEXT("/Engine/BasicShapes/Cube"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Iron(TEXT("/Game/SoulBreak/Materials/Characters/MI_Iron"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Brass(TEXT("/Game/SoulBreak/Materials/Characters/MI_Gilt"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Hide(TEXT("/Game/SoulBreak/Materials/Characters/MI_Leather"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Soul(TEXT("/Game/SoulBreak/Materials/Characters/MI_Soul"));
    auto Part=[&](const TCHAR* Name,USceneComponent* Parent,UStaticMesh* Mesh,UMaterialInterface* Material,
        FVector Pos,FVector Size,FRotator Rot=FRotator::ZeroRotator)
    {
        auto* P=CreateDefaultSubobject<UStaticMeshComponent>(Name);
        P->SetupAttachment(Parent); P->SetStaticMesh(Mesh);
        P->SetRelativeLocation(Pos); P->SetRelativeScale3D(Size*.01); P->SetRelativeRotation(Rot);
        P->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        P->SetMaterial(0,Material);
    };
    Part(TEXT("Foot"),RootComponent,Cylinder.Object,Iron.Object,{0,0,5},{70,70,10});
    Part(TEXT("FootLip"),RootComponent,Cylinder.Object,Brass.Object,{0,0,11},{53,53,3});
    Part(TEXT("Pillar"),RootComponent,Cylinder.Object,Hide.Object,{0,0,52},{14,14,90});
    Part(TEXT("Crossbar"),Target,Box.Object,Iron.Object,{0,0,44},{100,12,12});
    Part(TEXT("Straw"),Target,Sphere.Object,Hide.Object,{0,0,39},{60,36,73});
    Part(TEXT("Roundel"),Target,Cylinder.Object,Brass.Object,{0,-15,40},{57,57,5},FRotator(0,0,90));
    Part(TEXT("RoundelInset"),Target,Cylinder.Object,Iron.Object,{0,-19,40},{49,49,4},FRotator(0,0,90));
    Part(TEXT("Bullseye"),Target,Cylinder.Object,Brass.Object,{0,-22,40},{24,24,3},FRotator(0,0,90));
    Part(TEXT("Boss"),Target,Sphere.Object,Soul.Object,{0,-25,40},{13,6,13});
    Part(TEXT("Helmet"),Target,Sphere.Object,Iron.Object,{0,0,87},{31,28,32});
    Part(TEXT("Visor"),Target,Box.Object,Brass.Object,{0,-14,86},{23,4,3});
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
