#include "Combat/SBFighter.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Components/StaticMeshComponent.h"
#include "Materials/MaterialInterface.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"

ASBFighter::ASBFighter()
{
    PrimaryActorTick.bCanEverTick = true;
    bUseControllerRotationYaw = false;
    GetMesh()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    GetMesh()->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    GetCharacterMovement()->bOrientRotationToMovement = false;
    GetCharacterMovement()->bUseControllerDesiredRotation = false;
    GetCharacterMovement()->MaxStepHeight = 28.f;
}
void ASBFighter::BeginPlay()
{
    Super::BeginPlay();
    if (!CombatData) CombatData = LoadObject<USBCombatData>(nullptr,TEXT("/Game/SoulBreak/Data/DA_Combat.DA_Combat"),nullptr,LOAD_NoWarn);
    if (!CombatData) CombatData = GetMutableDefault<USBCombatData>();
}
void ASBFighter::LoadFighter(const FString& Name, float DesiredHeight)
{
    bHeavy = Name == TEXT("Knight");
    const FString MeshPath = FString::Printf(TEXT("/Game/SoulBreak/Characters/SK_%s.SK_%s"),*Name,*Name);
    if (!GetMesh()->GetSkeletalMeshAsset())
        if (USkeletalMesh* Mesh = LoadObject<USkeletalMesh>(nullptr,*MeshPath)) GetMesh()->SetSkeletalMesh(Mesh);
    AlignMesh(DesiredHeight);
    // A soft contact patch anchors the feet even at low shadow scalability.
    auto* Contact=NewObject<UStaticMeshComponent>(this);
    Contact->SetupAttachment(RootComponent);
    Contact->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Contact->SetCastShadow(false);
    Contact->SetCanEverAffectNavigation(false);
    Contact->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Plane.Plane")));
    Contact->SetMaterial(0,LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/SoulBreak/Materials/M_ContactShadow.M_ContactShadow")));
    Contact->SetRelativeScale3D(bHeavy ? FVector(1.4,1.15,1) : FVector(.93,.79,1));
    Contact->SetRelativeLocation(FVector(0,0,-GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight()+1.9));
    Contact->RegisterComponent();
    Clips = CombatData->Animations;
    Cues = CombatData->Sounds;
    for (const TCHAR* NamePart : {TEXT("Idle"),TEXT("Walk"),TEXT("OathCut"),TEXT("Run"),TEXT("Cut"),TEXT("ReturnCut"),TEXT("Evade"),TEXT("Parry"),TEXT("Stagger"),TEXT("Death"),TEXT("Stomp"),TEXT("SwordSweep"),TEXT("Bash")})
    {
        if (Clips.FindRef(FName(NamePart))) continue;
        const FString Asset = FString::Printf(TEXT("/Game/SoulBreak/Animations/AN_%s.AN_%s"),NamePart,NamePart);
        if (UAnimSequence* Anim = LoadObject<UAnimSequence>(nullptr,*Asset,nullptr,LOAD_NoWarn)) Clips.Add(FName(NamePart),Anim);
    }
    for (const TCHAR* Sound : {TEXT("Swing"),TEXT("Impact"),TEXT("Parry"),TEXT("Dodge"),TEXT("Break"),TEXT("Stomp"),TEXT("Shield"),TEXT("BodyHit"),TEXT("Step"),TEXT("HeavyStep")})
    {
        if (Cues.FindRef(FName(Sound))) continue;
        FString Asset = FString::Printf(TEXT("/Game/SoulBreak/Audio/S_%s.S_%s"),Sound,Sound);
        if (USoundBase* Cue = LoadObject<USoundBase>(nullptr,*Asset,nullptr,LOAD_NoWarn)) Cues.Add(FName(Sound),Cue);
    }
    Pose(TEXT("Idle"),true);
}
void ASBFighter::AlignMesh(float DesiredHeight)
{
    USkeletalMesh* Asset = GetMesh()->GetSkeletalMeshAsset();
    if (!Asset) return;
    const FBoxSphereBounds Bounds = Asset->GetBounds();
    const float Scale = DesiredHeight / FMath::Max(1.f,float(Bounds.BoxExtent.Z * 2));
    const auto& Skeleton = Asset->GetRefSkeleton();
    auto RestLocation = [&Skeleton](int32 Index) {
        FTransform T = Skeleton.GetRefBonePose()[Index];
        while ((Index = Skeleton.GetParentIndex(Index)) != INDEX_NONE) T *= Skeleton.GetRefBonePose()[Index];
        return T.GetTranslation();
    };
    int32 Front = Skeleton.FindBoneIndex(TEXT("Forward")), Hips = Skeleton.FindBoneIndex(TEXT("Pelvis"));
    float AssetYaw = -90;
    if (Front != INDEX_NONE && Hips != INDEX_NONE)
        AssetYaw = (RestLocation(Front) - RestLocation(Hips)).Rotation().Yaw;
    GetMesh()->SetRelativeRotation(FRotator(0,-AssetYaw,0));
    GetMesh()->SetRelativeScale3D(FVector(Scale));
    GetMesh()->SetRelativeLocation(FVector(0,0,-GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight() - (Bounds.Origin.Z - Bounds.BoxExtent.Z)*Scale));
}
void ASBFighter::Pose(FName Clip, bool bLoop, float Duration, bool bRestart)
{
    if (!bRestart && CurrentClip == Clip) return;
    CurrentClip = Clip;
    if (TObjectPtr<UAnimSequence>* Sequence = Clips.Find(Clip))
    {
        GetMesh()->PlayAnimation(*Sequence,bLoop);
        GetMesh()->SetPlayRate(Duration > 0 ? (*Sequence)->GetPlayLength()/Duration : 1.f);
    }
}
void ASBFighter::PlayCue(FName Name,float Volume,float Pitch)
{
    if (auto* Sound = Cues.Find(Name)) UGameplayStatics::PlaySoundAtLocation(this,*Sound,GetActorLocation(),Volume,Pitch);
}
void ASBFighter::Face(const FVector& D,float Degrees)
{
    if (D.IsNearlyZero()) return;
    float Yaw = FMath::FixedTurn(GetActorRotation().Yaw,D.Rotation().Yaw,Degrees);
    SetActorRotation(FRotator(0,Yaw,0));
}
void ASBFighter::Locomotion(float WalkSpeed)
{
    float Speed = GetVelocity().Size2D();
    Pose(Speed < 10 ? FName(TEXT("Idle")) : Speed <= WalkSpeed + 20 ? FName(TEXT("Walk")) : FName(TEXT("Run")),true);
    if (Speed > 40 && GetWorld()->TimeSeconds >= NextStep)
    {
        PlayCue(bHeavy ? TEXT("HeavyStep") : TEXT("Step"), bHeavy ? .45f : .23f);
        NextStep = GetWorld()->TimeSeconds + (Speed > WalkSpeed + 20 ? .29f : .42f);
    }
}
void ASBFighter::Tick(float Dt)
{
    Super::Tick(Dt);
    HitPulse = FMath::Max(0.f,HitPulse-Dt*3.5f);
}
