#include "Combat/SBGroundDust.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Materials/MaterialInterface.h"
#include "UObject/ConstructorHelpers.h"

ASBGroundDust::ASBGroundDust()
{
    PrimaryActorTick.bCanEverTick=true;
    Clouds=CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("Limestone dust"));
    SetRootComponent(Clouds);
    Clouds->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Clouds->SetCanEverAffectNavigation(false);
    Clouds->SetCastShadow(false);
    Clouds->NumCustomDataFloats=1;
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Card(TEXT("/Engine/BasicShapes/Plane"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Dust(TEXT("/Game/SoulBreak/FX/M_StoneDust"));
    Clouds->SetStaticMesh(Card.Object);
    Clouds->SetMaterial(0,Dust.Object);
}

void ASBGroundDust::Kick(UWorld* World,const FVector& Floor,const FVector& Travel,float Radius)
{
    auto* Emitter=World->SpawnActor<ASBGroundDust>(Floor,FRotator::ZeroRotator);
    if (!Emitter) return;
    Emitter->Reach=Radius;
    Emitter->Direction=Travel.GetSafeNormal2D();
    const int32 Count=Emitter->Direction.IsNearlyZero() ? 16 : 9;
    for (int32 I=0;I<Count;++I)
        Emitter->Clouds->AddInstance(FTransform(FQuat::Identity,FVector::ZeroVector,FVector::ZeroVector));
    Emitter->SetLifeSpan(.95f);
}

void ASBGroundDust::Tick(float Dt)
{
    Super::Tick(Dt);
    Age+=Dt;
    const auto* PC=GetWorld()->GetFirstPlayerController();
    if (!PC || !PC->PlayerCameraManager) return;
    const FVector View=PC->PlayerCameraManager->GetCameraLocation()-GetActorLocation();
    const int32 Count=Clouds->GetInstanceCount();
    for (int32 I=0;I<Count;++I)
    {
        const float Phase=FMath::Clamp((Age-.018f*(I%5))/(.56f+.06f*(I%6)),0.f,1.f);
        const float Spread=1.f-FMath::Square(1.f-Phase);
        const float Angle=I*2.39996f;
        FVector Outward(FMath::Cos(Angle),FMath::Sin(Angle),0.f);
        if (!Direction.IsNearlyZero()) Outward=(Outward*.59f-Direction).GetSafeNormal2D();
        FVector Offset=Outward*Reach*(.08f+Spread*(.58f+.067f*(I%6)));
        Offset.Z=4.f+Spread*(15.f+3.f*(I%5));
        const float Size=.28f+Spread*(.48f+.09f*(I%5));
        const FVector TowardEye=(View-Offset).GetSafeNormal();
        const FQuat Facing=FQuat(TowardEye,Angle*.45f)*FRotationMatrix::MakeFromZ(TowardEye).ToQuat();
        const bool Last=(I+1==Count);
        Clouds->SetCustomDataValue(I,0,FMath::Min(1.f,Phase*11.f)*FMath::Square(1.f-Phase)*.42f,false);
        Clouds->UpdateInstanceTransform(I,FTransform(Facing,Offset,FVector(Size*1.35f,Size,1.f)),false,Last,true);
    }
}
