#include "Combat/SBImpact.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "EngineUtils.h"
#include "Materials/MaterialInstanceDynamic.h"

ASBImpact::ASBImpact()
{
    PrimaryActorTick.bCanEverTick=true;
    SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Origin")));
    Sword=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("DiscardedSword")); Sword->SetupAttachment(RootComponent);
    Chips=CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("Sparks")); Chips->SetupAttachment(RootComponent);
    Chips->SetCastShadow(false);
    for (UPrimitiveComponent* Part : {static_cast<UPrimitiveComponent*>(Sword),static_cast<UPrimitiveComponent*>(Chips)})
    {
        Part->SetCollisionEnabled(ECollisionEnabled::NoCollision); Part->SetCanEverAffectNavigation(false);
    }
}
void ASBImpact::Launch(UStaticMesh* Blade,const FVector& Velocity,float FloorZ,float Scale,FLinearColor Tint,float Size)
{
    Ground=FloorZ-GetActorLocation().Z; LaunchSpeed=Velocity; bFallenBlade=Blade!=nullptr; ShardSize=Size;
    if (Blade) { Sword->SetStaticMesh(Blade); Sword->SetWorldScale3D(FVector(Scale)); }
    else
    {
        int32 Count=0;
        for (TActorIterator<ASBImpact> I(GetWorld());I;++I)
            if (!I->bFallenBlade && !I->IsActorBeingDestroyed()) ++Count;
        if (Count>8) { Destroy(); return; }
        SetLifeSpan(1.f);
    }
    Chips->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));
    if (auto* Mat=UMaterialInstanceDynamic::Create(LoadObject<UMaterialInterface>(nullptr,TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial")),this))
    {
        Mat->SetVectorParameterValue(TEXT("Color"),Tint); Chips->SetMaterial(0,Mat);
    }
    const int32 N=Blade ? 6 : 5;
    for (int32 I=0;I<N;++I)
    {
        const float A=(I+.2f)*2*PI/N;
        Speeds.Add(FVector(FMath::Cos(A)*(70+18*I),FMath::Sin(A)*(80+15*I),120+24*I));
        Chips->AddInstance(FTransform(FQuat::Identity,FVector::ZeroVector,FVector(.01f)));
    }
}
void ASBImpact::Tick(float Dt)
{
    Super::Tick(Dt);
    Age+=Dt;
    for (int32 I=0;I<Speeds.Num();++I)
    {
        FVector P=Speeds[I]*Age+FVector(0,0,-550*Age*Age); P.Z=FMath::Max(float(P.Z),Ground+1);
        float S=FMath::Max(0.f,1.f-Age); S*=ShardSize*(bFallenBlade ? .13f:.065f);
        Chips->UpdateInstanceTransform(I,FTransform(FRotator(Age*320,Age*500+I*67,0),P,FVector(S,S*.31,S*.19)),false,I==Speeds.Num()-1,true);
    }
    if (bFallenBlade)
    {
        FVector P=LaunchSpeed*Age+FVector(0,0,-490*Age*Age);
        bool Land=P.Z<=Ground+5;
        P.Z=FMath::Max(float(P.Z),Ground+5); Sword->SetRelativeLocation(P);
        Sword->SetRelativeRotation(Land ? FRotator(0,61,0):FRotator(0,Age*220,Age*300));
        if (Land && Age>=1) {Chips->ClearInstances();SetActorTickEnabled(false);}
    }
}
