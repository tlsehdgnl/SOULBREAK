#include "Combat/SBTrainingDummy.h"
#include "Components/StaticMeshComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"
#include "Combat/SBImpact.h"
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
    auto* Rack=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Armor rack"));
    Rack->SetupAttachment(RootComponent);
    Rack->SetRelativeLocation(FVector(0,260,0));
    Rack->SetStaticMesh(StandMesh.Object);
    Rack->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Rack->SetRelativeScale3D(FVector(1,1,1.45));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> ArmMesh(TEXT("/Game/SoulBreak/Characters/SM_RackArm"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> ShieldMesh(TEXT("/Game/SoulBreak/Characters/SM_FallenShield"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> KneeMesh(TEXT("/Game/SoulBreak/Characters/SM_FallenKnee"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Timber(TEXT("/Engine/BasicShapes/Cube"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Oak(TEXT("/Game/SoulBreak/Environment/MI_Chapel_Oak"));
    auto Rail=[&](FName Name,FVector A,FVector B,float Width)
    {
        auto* Bar=CreateDefaultSubobject<UStaticMeshComponent>(Name);
        Bar->SetupAttachment(RootComponent);
        Bar->SetStaticMesh(Timber.Object); Bar->SetMaterial(0,Oak.Object);
        Bar->SetRelativeLocation((A+B)*.5+FVector(0,260,0));
        Bar->SetRelativeRotation(FRotationMatrix::MakeFromZ(B-A).ToQuat());
        Bar->SetRelativeScale3D(FVector(Width/100,Width/100,(B-A).Size()/100));
        Bar->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    };
    Rail(TEXT("Rack spine"),{-4,0,65},{-4,0,210},9);
    Rail(TEXT("Arm crossbar"),{-4,4,203},{-4,-46,203},7);
    Rail(TEXT("Shield crossbar"),{-4,-4,151},{4,46,151},7);
    Rail(TEXT("Knee peg"),{-4,0,71},{10,17,71},5);
    auto Mount=[&](FName Name,UStaticMesh* Mesh,const FVector& Position)
    {
        auto* Plate=CreateDefaultSubobject<UStaticMeshComponent>(Name);
        Plate->SetupAttachment(RootComponent);
        Plate->SetRelativeLocation(Position+FVector(0,260,0));
        Plate->SetRelativeRotation(FRotator(0,-90,0));
        Plate->SetRelativeScale3D(FVector(1.45));
        Plate->SetStaticMesh(Mesh);
        Plate->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Plates.Add(Plate);
    };
    Mount(TEXT("Practice sword arm"),ArmMesh.Object,{0,-45,207});
    Mount(TEXT("Practice shield"),ShieldMesh.Object,{10,49,150});
    Mount(TEXT("Practice poleyn"),KneeMesh.Object,{12,15,71});
}
FVector ASBTrainingDummy::RackPoint(ESBArmorPart Part) const
{
    if (Part==ESBArmorPart::Body) return GetActorTransform().TransformPosition(FVector(0,260,137));
    const auto* Plate=Plates[int32(Part)-1].Get();
    return Plate->GetComponentLocation()+(Part==ESBArmorPart::SwordArm ? FVector(0,0,-22) : FVector::ZeroVector);
}
bool ASBTrainingDummy::TraceRack(const FVector& From,const FVector& To,ESBArmorPart Part,bool bFocused) const
{
    const float Height=Part==ESBArmorPart::Shield ? 18.f : Part==ESBArmorPart::SwordArm ? 14.f : 4.f;
    const float Radius=Part==ESBArmorPart::Knee ? 20.f : 26.f;
    const FVector Center=RackPoint(Part), Half(0,0,Height);
    FVector A,B;
    FMath::SegmentDistToSegmentSafe(From,To,Center-Half,Center+Half,A,B);
    return FVector::DistSquared(A,B)<=FMath::Square(Radius+(bFocused && Part==ESBArmorPart::SwordArm ? 27.f : bFocused ? 18.f : 12.f));
}
void ASBTrainingDummy::HitRack(ESBArmorPart Part,int32 AttackId)
{
    if (AttackId<=LastHitId) return;
    LastHitId=AttackId; LastRackHit=Part; RackPulse=.65f;
    const FVector P=RackPoint(Part);
    UGameplayStatics::PlaySoundAtLocation(this,Impact,P,.7f,1.12f);
    if (auto* Fx=GetWorld()->SpawnActor<ASBImpact>(P,GetActorRotation()))
        Fx->Launch(nullptr,FVector::ZeroVector,GetActorLocation().Z,1,FLinearColor(.22f,.68f,1));
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
    RackPulse=FMath::Max(0.f,RackPulse-Dt);
    for (int I=0;I<Plates.Num();++I)
    {
        const float Ring=int32(LastRackHit)==I+1 ? 8.f*RackPulse*FMath::Sin(RackPulse*33) : 0.f;
        Plates[I]->SetRelativeRotation(FRotator(0,-90,Ring));
    }
    RestSeconds+=Dt;
    if (RestSeconds>4) Health=100;
    Target->SetRelativeRotation(FRotator(0,0,HitPulse*FMath::Sin(RestSeconds*24.f)*16));
}
