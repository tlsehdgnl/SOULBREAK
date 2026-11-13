#include "Core/SBCathedralGate.h"
#include "Components/StaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/BoxComponent.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInterface.h"
#include "UObject/ConstructorHelpers.h"

ASBCathedralGate::ASBCathedralGate()
{
    SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Threshold")));
    PassageSeal=CreateDefaultSubobject<UBoxComponent>(TEXT("Sealed passage"));
    PassageSeal->SetupAttachment(RootComponent);
    PassageSeal->SetRelativeLocation(FVector(0,0,177));
    PassageSeal->SetBoxExtent(FVector(12,185,180));
    PassageSeal->SetCollisionProfileName(TEXT("BlockAllDynamic"));
    PassageSeal->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    PassageSeal->SetGenerateOverlapEvents(false);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Stone(TEXT("/Game/SoulBreak/Environment/MI_Chapel_Ashlar"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Trim(TEXT("/Game/SoulBreak/Environment/MI_Chapel_Carving"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Oak(TEXT("/Game/SoulBreak/Environment/MI_Chapel_Oak"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Iron(TEXT("/Game/SoulBreak/Materials/Characters/MI_Iron"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Bronze(TEXT("/Game/SoulBreak/Materials/Characters/MI_Bronze"));
    auto Block=[&](FName Name,USceneComponent* Parent,FVector Center,FVector Size,UMaterialInterface* Mat)
    {
        auto* Mesh=CreateDefaultSubobject<UStaticMeshComponent>(Name);
        Mesh->SetupAttachment(Parent); Mesh->SetStaticMesh(Cube.Object); Mesh->SetMaterial(0,Mat);
        Mesh->SetRelativeLocation(Center); Mesh->SetRelativeScale3D(Size/100.);
        Mesh->SetCollisionProfileName(TEXT("BlockAllDynamic"));
        return Mesh;
    };
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Paving(TEXT("/Game/SoulBreak/Environment/MI_Chapel_Pavement"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Vault(TEXT("/Game/SoulBreak/Environment/MI_Chapel_VaultWeb"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Gold(TEXT("/Game/SoulBreak/Environment/MI_Chapel_Burnished"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Velvet(TEXT("/Game/SoulBreak/Environment/MI_Chapel_Velvet"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Wick(TEXT("/Game/SoulBreak/Environment/MI_Chapel_Wick"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Sphere(TEXT("/Engine/BasicShapes/Sphere"));
    auto* Fill=CreateDefaultSubobject<UPointLightComponent>(TEXT("Vault bounce"));
    Fill->SetupAttachment(RootComponent); Fill->SetRelativeLocation({-510,0,395});
    Fill->SetIntensityUnits(ELightUnits::Lumens); Fill->SetIntensity(580); Fill->SetAttenuationRadius(1100);
    Fill->SetLightColor(FLinearColor(.75f,.84f,1.f)); Fill->SetCastShadows(false);
    Block(TEXT("Vestibule floor"),RootComponent,{-412,0,-20},{1024,944,40},Paving.Object);
    Block(TEXT("Vestibule west wall"),RootComponent,{-908,0,270},{32,944,540},Stone.Object);
    Block(TEXT("Vestibule ceiling"),RootComponent,{-452,0,540},{936,944,32},Vault.Object);
    Block(TEXT("Upper screen"),RootComponent,{0,0,677},{62,2180,650},Stone.Object);
    Block(TEXT("Lintel"),RootComponent,{0,0,366},{84,470,32},Trim.Object);
    // Two arcs meet above the lintel, echoing the pointed vaults beyond the doors.
    for (int Side : {-1,1})
    {
        for (int Segment=0; Segment<9; ++Segment)
        {
            auto Point=[Side](int Index)
            {
                const float A=FMath::DegreesToRadians(Index*60.f/9.f);
                return FVector(-49,Side*(360.f*FMath::Cos(A)-180.f),201.f+360.f*FMath::Sin(A));
            };
            const FVector A=Point(Segment), B=Point(Segment+1);
            auto* StoneRib=Block(FName(*FString::Printf(TEXT("Archivolt_%d_%d"),Side,Segment)),RootComponent,
                (A+B)*.5,{22,22,FVector::Distance(A,B)-1.5},Trim.Object);
            StoneRib->SetRelativeRotation(FRotationMatrix::MakeFromZ(B-A).Rotator());
            StoneRib->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        }
    }
    for (int Side : {-1,1})
    {
        auto Name=[Side](const TCHAR* Base){return FName(*FString::Printf(TEXT("%s_%d"),Base,Side));};
        Block(Name(TEXT("Vestibule aisle")),RootComponent,{-452,Side*464.,270},{936,32,540},Stone.Object);
        for (int Bay=0;Bay<3;++Bay)
        {
            const double X=-190.-Bay*285.;
            Block(FName(*FString::Printf(TEXT("Side pier_%d_%d"),Side,Bay)),RootComponent,{X,Side*442.,165},{50,52,330},Trim.Object);
            auto* Rib=Block(FName(*FString::Printf(TEXT("Vault rib_%d_%d"),Side,Bay)),RootComponent,{X,Side*222.,430},{34,488,24},Trim.Object);
            Rib->SetRelativeRotation(FRotator(0,0,Side*24.f));
            const auto Detail=[&](const TCHAR* Part){return FName(*FString::Printf(TEXT("%s_%d_%d"),Part,Side,Bay));};
            Block(Detail(TEXT("Velvet hanging")),RootComponent,{X+64,Side*444.,280},{70,4,150},Velvet.Object);
            Block(Detail(TEXT("Banner rail")),RootComponent,{X+64,Side*440.,356},{84,8,6},Gold.Object);
            Block(Detail(TEXT("Banner embroidery")),RootComponent,{X+64,Side*440.,284},{5,2,125},Gold.Object);
            Block(Detail(TEXT("Lamp arm")),RootComponent,{X,Side*404.,192},{13,74,9},Bronze.Object);
            auto* Bowl=Block(Detail(TEXT("Lamp cup")),RootComponent,{X,Side*374.,201},{38,38,18},Gold.Object);
            Bowl->SetStaticMesh(Sphere.Object);
            auto* Flame=Block(Detail(TEXT("Lamp flame")),RootComponent,{X,Side*374.,217},{12,12,26},Wick.Object);
            Flame->SetStaticMesh(Sphere.Object);
            auto* Light=CreateDefaultSubobject<UPointLightComponent>(Detail(TEXT("Sconce light")));
            Light->SetupAttachment(RootComponent); Light->SetRelativeLocation({X,Side*360.,226});
            Light->SetIntensityUnits(ELightUnits::Lumens); Light->SetIntensity(170); Light->SetAttenuationRadius(680);
            Light->SetLightColor(FLinearColor(1.f,.64f,.35f)); Light->SetCastShadows(false);
        }
        Block(Name(TEXT("Screen")),RootComponent,{0,Side*635.,176},{62,910,352},Stone.Object);
        Block(Name(TEXT("Plinth")),RootComponent,{0,Side*635.,22},{84,910,44},Trim.Object);
        Block(Name(TEXT("Cornice")),RootComponent,{0,Side*635.,348},{88,910,22},Trim.Object);
        Block(Name(TEXT("Door jamb")),RootComponent,{0,Side*200.,174},{88,40,348},Trim.Object);
        for (int Bay=0;Bay<3;++Bay)
        {
            const double Y=Side*(300.+Bay*295.);
            Block(FName(*FString::Printf(TEXT("Stone pier_%d_%d"),Side,Bay)),RootComponent,{0,Y,227},{92,40,454},Trim.Object);
            Block(FName(*FString::Printf(TEXT("Pier capital_%d_%d"),Side,Bay)),RootComponent,{0,Y,445},{110,66,28},Trim.Object);
        }
        auto* Hinge=CreateDefaultSubobject<USceneComponent>(Name(TEXT("Hinge")));
        Hinge->SetupAttachment(RootComponent); Hinge->SetRelativeLocation({0,Side*180.,0});
        if (Side<0) LeftHinge=Hinge; else RightHinge=Hinge;
        Block(Name(TEXT("Door leaf")),Hinge,{0,-Side*90.,175},{20,180,350},Oak.Object);
        for (int Face : {-1,1})
        {
            for (int Panel=0;Panel<2;++Panel)
            {
                const double Y=-Side*(48.+84*Panel);
                auto Detail=[&](const TCHAR* Part){return FName(*FString::Printf(TEXT("%s_%d_%d_%d"),Part,Side,Face,Panel));};
                Block(Detail(TEXT("Inset panel")),Hinge,{Face*11.,Y,175},{5,70,286},Iron.Object);
                Block(Detail(TEXT("Oak panel")),Hinge,{Face*14.,Y,172},{4,60,269},Oak.Object);
                auto* Emblem=Block(Detail(TEXT("Gilt lozenge")),Hinge,{Face*17.,Y,233},{3,29,29},Gold.Object);
                Emblem->SetRelativeRotation(FRotator(0,0,45));
                Block(Detail(TEXT("Gilt spine")),Hinge,{Face*17.,Y,163},{3,4,138},Gold.Object);
            }
        }
        for (int Row=0;Row<3;++Row)
            Block(FName(*FString::Printf(TEXT("Band_%d_%d"),Side,Row)),Hinge,{-12,-Side*90.,55.+120*Row},{5,174,8},Bronze.Object);
        Block(Name(TEXT("Pull")),Hinge,{-18,-Side*154.,129},{14,6,36},Iron.Object);
        auto* Lamp=CreateDefaultSubobject<UPointLightComponent>(Name(TEXT("Gate light")));
        Lamp->SetupAttachment(RootComponent); Lamp->SetRelativeLocation({-130,Side*225.,255});
        Lamp->SetLightColor(FLinearColor(1.f,.54f,.24f)); Lamp->SetIntensity(1100); Lamp->SetAttenuationRadius(850);
    }
}
void ASBCathedralGate::SetOpening(float Alpha)
{
    const float Angle=95.f*FMath::SmoothStep(0.f,1.f,Alpha);
    LeftHinge->SetRelativeRotation(FRotator(0,-Angle,0));
    RightHinge->SetRelativeRotation(FRotator(0,Angle,0));
}
void ASBCathedralGate::SealPassage()
{
    PassageSeal->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
    for (USceneComponent* Hinge : {LeftHinge.Get(),RightHinge.Get()})
    {
        for (USceneComponent* Child : Hinge->GetAttachChildren())
            if (auto* Primitive=Cast<UPrimitiveComponent>(Child))
                Primitive->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    }
}

void ASBCathedralGate::UnsealPassage()
{
    PassageSeal->SetCollisionEnabled(ECollisionEnabled::NoCollision);
}
