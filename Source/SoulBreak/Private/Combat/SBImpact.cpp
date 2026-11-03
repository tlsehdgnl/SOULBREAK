#include "Combat/SBImpact.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "EngineUtils.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"

ASBImpact::ASBImpact()
{
    PrimaryActorTick.bCanEverTick = true;
    SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Impact origin")));
    Sword = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Fallen blade"));
    Sparks = CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("Hot filings"));
    Fragments = CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("Splintered plate"));
    for (UStaticMeshComponent* Part : {Sword.Get(),static_cast<UStaticMeshComponent*>(Sparks),static_cast<UStaticMeshComponent*>(Fragments)})
    {
        Part->SetupAttachment(RootComponent);
        Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Part->SetGenerateOverlapEvents(false);
        Part->SetCanEverAffectNavigation(false);
    }
    Sparks->SetCastShadow(false);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Bead(TEXT("/Engine/BasicShapes/Sphere"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Splinter(TEXT("/Engine/BasicShapes/Cone"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Bronze(TEXT("/Game/SoulBreak/Materials/Characters/MI_Bronze"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Glow(TEXT("/Game/SoulBreak/FX/M_BladeLight"));
    Sparks->SetStaticMesh(Bead.Object);
    Fragments->SetStaticMesh(Splinter.Object);
    Fragments->SetMaterial(0,Bronze.Object);
    LightMaterial = Glow.Object;
    Flash = CreateDefaultSubobject<UPointLightComponent>(TEXT("Contact light"));
    Flash->SetupAttachment(RootComponent);
    Flash->SetCastShadows(false);
    Flash->SetIntensityUnits(ELightUnits::Lumens);
    Flash->SetIntensity(0.f);
}
void ASBImpact::Launch(UStaticMesh* Blade, const FVector& Velocity, float FloorZ, float Scale, FLinearColor Tint, float Size)
{
    Ground = FloorZ - GetActorLocation().Z + 4.f;
    LaunchSpeed = Velocity;
    ShardSize = Size;
    bFallenBlade = Blade != nullptr;
    if (Blade)
    {
        Sword->SetStaticMesh(Blade);
        Sword->SetWorldScale3D(FVector(Scale));
        LandTime = (Velocity.Z+FMath::Sqrt(FMath::Max(0.,Velocity.Z*Velocity.Z-1960.*Ground)))/980.;
    }
    else
    {
        int32 Count = 0;
        for (TActorIterator<ASBImpact> It(GetWorld()); It; ++It)
            if (!It->bFallenBlade && !It->IsActorBeingDestroyed()) ++Count;
        if (Count>8) { Destroy(); return; }
        SetLifeSpan(.52f);
    }
    Flash->SetLightColor(FLinearColor::LerpUsingHSV(Tint,FLinearColor::White,.25f));
    Flash->SetAttenuationRadius(Blade ? 270.f : 145.f);
    Flash->SetIntensity(Blade ? 380.f : 165.f);
    if (LightMaterial)
    {
        UMaterialInstanceDynamic* M=UMaterialInstanceDynamic::Create(LightMaterial,this);
        M->SetVectorParameterValue(TEXT("Tint"),Tint);
        M->SetScalarParameterValue(TEXT("Energy"),4.2f);
        Sparks->SetMaterial(0,M);
    }
    const int32 N=Blade ? 16 : 9;
    for (int32 I=0; I<N; ++I)
    {
        // Golden-angle distribution avoids an evenly-spaced star at the contact point.
        const float A=I*2.39996f;
        const float Speed=(110.f + (I*73)%215)*Size;
        SparkVelocity.Add(FVector(FMath::Cos(A)*Speed,FMath::Sin(A)*Speed,40.f+(I*47)%210));
        Sparks->AddInstance(FTransform(FQuat::Identity,FVector::ZeroVector,FVector(.003)));
    }
    if (Blade)
    {
        for (int32 I=0; I<6; ++I)
        {
            const float A=I*2.39996f;
            FragmentVelocity.Add(FVector(110.f*FMath::Cos(A),100.f*FMath::Sin(A),150.f+I*17.f));
            Fragments->AddInstance(FTransform::Identity);
        }
    }
    Tick(0.f);
}
void ASBImpact::Tick(float Dt)
{
    Super::Tick(Dt);
    Age+=Dt;
    const float FlashAlpha=FMath::Max(0.f,1.f-Age/(bFallenBlade ? .16f : .09f));
    Flash->SetIntensity((bFallenBlade ? 380.f : 165.f)*FlashAlpha*FlashAlpha);
    for (int32 I=0; I<SparkVelocity.Num(); ++I)
    {
        const float Life=.18f+(I%5)*.055f;
        const float T=FMath::Min(Age,Life);
        FVector P=SparkVelocity[I]*T+FVector(0,0,-480.f*T*T);
        P.Z=FMath::Max(P.Z,double(Ground));
        const FVector Flight=SparkVelocity[I]-FVector(0,0,960.f*T);
        const float Fade=FMath::Max(0.f,1.f-Age/Life)*ShardSize;
        const FVector Extent((.08f+.018f*(I%4))*Fade,.009f*Fade,.009f*Fade);
        Sparks->UpdateInstanceTransform(I,FTransform(Flight.Rotation(),P,Extent),false,I+1==SparkVelocity.Num(),true);
    }
    for (int32 I=0; I<FragmentVelocity.Num(); ++I)
    {
        FVector P=FragmentVelocity[I]*Age+FVector(0,0,-490.f*Age*Age);
        P.Z=FMath::Max(P.Z,double(Ground));
        const float Fade=FMath::Clamp((1.f-Age)*5.f,0.f,1.f);
        const FRotator Spin(47.f*I+Age*320.f,67.f*I+Age*195.f,24.f*I);
        Fragments->UpdateInstanceTransform(I,FTransform(Spin,P,FVector(.12,.045,.15)*Fade),false,I+1==FragmentVelocity.Num(),true);
    }
    if (bFallenBlade)
    {
        float Flight=FMath::Min(Age,LandTime);
        const FVector P=LaunchSpeed*Flight+FVector(0,0,-490.f*Flight*Flight);
        Sword->SetRelativeLocation(P);
        float Roll=Age*340.f;
        if (Age>=LandTime) Roll=FMath::Exp(-16.f*(Age-LandTime))*FMath::Sin((Age-LandTime)*30.f)*12.f;
        Sword->SetRelativeRotation(FRotator(0,FMath::Min(Flight*210.f,90.f),Roll));
        if (Age>=FMath::Max(1.f,LandTime+.35f))
        {
            Fragments->ClearInstances();
            Sparks->ClearInstances();
            Flash->SetVisibility(false);
            SetActorTickEnabled(false);
        }
    }
}
