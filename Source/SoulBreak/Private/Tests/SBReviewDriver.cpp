#include "Tests/SBReviewDriver.h"
#if !UE_BUILD_SHIPPING && !UE_BUILD_TEST
#include "Core/SBGameMode.h"
#include "Player/SBHero.h"
#include "Boss/SBKnight.h"
#include "AudioMixerBlueprintLibrary.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "GameFramework/Controller.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"
#include "HAL/PlatformMisc.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Scalability.h"
#include "UnrealClient.h"

namespace
{
// Capturing continues across map reloads so the viewer can see the new encounter.
struct FReviewSession
{
    float Elapsed = 0;
    int32 Frame = 0;
    int32 Attempt = 0;
    double NextSnapshot = 0;
    bool AudioStarted = false;
    bool Finished = false;
} Session;

void Append(const FString& Path, const FString& Line)
{
    FFileHelper::SaveStringToFile(Line + LINE_TERMINATOR, *Path, FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM,
        &IFileManager::Get(), FILEWRITE_Append);
}

void MoveToward(ASBHero& Hero, const FVector& Target, float SlowRadius)
{
    const FVector Offset = Target - Hero.GetActorLocation();
    const FVector Direction = Offset.GetSafeNormal2D() * FMath::Min(1.f, static_cast<float>(Offset.Size2D())/SlowRadius);
    const FRotationMatrix ViewAxes(FRotator(0, Hero.GetControlRotation().Yaw, 0));
    Hero.SetMoveStick(FVector2D(FVector::DotProduct(Direction, ViewAxes.GetUnitAxis(EAxis::Y)),
        FVector::DotProduct(Direction, ViewAxes.GetUnitAxis(EAxis::X))));
}
}
#endif

ASBReviewDriver::ASBReviewDriver()
{
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.TickGroup = TG_PostUpdateWork;
}

void ASBReviewDriver::BeginPlay()
{
    Super::BeginPlay();
#if !UE_BUILD_SHIPPING && !UE_BUILD_TEST
    bPerf = FParse::Param(FCommandLine::Get(), TEXT("SBPerf"));
    bVideo = !bPerf && FParse::Param(FCommandLine::Get(), TEXT("SBVideoFrames"));
    if (!bPerf && !FParse::Param(FCommandLine::Get(), TEXT("SBDemo"))) { Destroy(); return; }
    if (!FParse::Value(FCommandLine::Get(), TEXT("SBOut="), OutputDirectory))
        OutputDirectory = FPaths::ProjectSavedDir() / TEXT("QA") / (bPerf ? TEXT("Performance") : TEXT("Demo"));
    OutputDirectory = FPaths::ConvertRelativePathToFull(OutputDirectory);
    IFileManager::Get().MakeDirectory(*OutputDirectory,true);
    if (bVideo) IFileManager::Get().MakeDirectory(*(OutputDirectory / TEXT("Frames")),true);
    if (++Session.Attempt == 1)
    {
        if (bPerf)
        {
            Scalability::FQualityLevels Quality;
            Quality.SetFromSingleQualityLevel(1);
            Scalability::SetQualityLevels(Quality);
            for (const TCHAR* Name : {TEXT("r.VSync"), TEXT("t.MaxFPS")})
                if (auto* Var = IConsoleManager::Get().FindConsoleVariable(Name)) Var->Set(0, ECVF_SetByCode);
            Append(OutputDirectory / TEXT("summary.csv"), TEXT("run,seconds,frames,p95_ms,viewport_width,viewport_height"));
        }
        else
        {
            Append(OutputDirectory / TEXT("events.csv"), TEXT("game_seconds,frame,attempt,event,player_health,boss_health,arm_health"));
            if (bVideo)
            {
                UAudioMixerBlueprintLibrary::StartRecordingOutput(this,80);
                Session.AudioStarted = true;
            }
        }
    }
    PreviousFrame = FPlatformTime::Seconds();
#else
    Destroy();
#endif
}
void ASBReviewDriver::Tick(float Dt)
{
    Super::Tick(Dt);
#if !UE_BUILD_SHIPPING && !UE_BUILD_TEST
    const double Now = FPlatformTime::Seconds();
    const float WallFrameMs = 1000.0*(Now - PreviousFrame);
    PreviousFrame = Now;
    if (Session.Finished) return;
    ASBGameMode* Mode = GetWorld()->GetAuthGameMode<ASBGameMode>();
    if (!Mode || !Mode->Hero || !Mode->Knight) return;
    Session.Elapsed += Dt;
    if (bFinishing)
    {
        if (Now - SampleWindow > 2) { Session.Finished = true; FPlatformMisc::RequestExit(false); }
        return;
    }
    Drive(*Mode, *Mode->Hero, *Mode->Knight);
    if (bPerf) Measure(Now, WallFrameMs, *Mode->Knight);
    else
    {
        Capture(*Mode, *Mode->Hero, *Mode->Knight);
        if (Session.Elapsed >= 70.f) Finish();
        else if ((Mode->Encounter == ESBEncounter::Victory || Mode->Encounter == ESBEncounter::Defeat) && Mode->OutcomeSeconds > 3.f)
            Mode->Retry();
    }
#endif
}
#if !UE_BUILD_SHIPPING && !UE_BUILD_TEST
void ASBReviewDriver::Drive(ASBGameMode& Game, ASBHero& Hero, ASBKnight& Knight)
{
    Hero.SetMoveStick(FVector2D::ZeroVector);
    if (Game.Encounter == ESBEncounter::Approach)
    {
        if (Session.Elapsed > 2 || bPerf)
            MoveToward(Hero, Knight.GetActorLocation(), 70.f);
        return;
    }
    if (Game.Encounter != ESBEncounter::Fighting) return;
    if (!Hero.bLockedOn) Hero.ToggleLock();
    // Performance setup is explicit: P2 with an actually broken arm, health refilled for a nonlethal workload.
    // The playable demo never writes either fighter's state or deals scripted damage.
    if (bPerf)
    {
        if (!Knight.bArmBroken) Knight.ApplySwordHit(0, 90.f, true);
        Hero.Health = 100.f;
        Knight.Health = 300.f;
    }
    const FVector Facing = Knight.GetActorForwardVector();
    const FVector Flank = Knight.GetActorRightVector();
    const float Distance = FVector::Dist2D(Hero.GetActorLocation(), Knight.GetActorLocation());
    const FVector Goal = Knight.GetActorLocation() + 81.f*Facing + (Knight.bArmBroken ? 17.f : 51.f)*Flank;
    MoveToward(Hero, Goal, 55.f);
    const bool Sword = Knight.Action == ESBKnightAction::SwordSweep;
    const bool Bash = Knight.Action == ESBKnightAction::Bash;
    const bool Stomp = Knight.Action == ESBKnightAction::Stomp;
    const float ToImpact = Knight.TelegraphDuration - Knight.PatternElapsed;
    if (!Knight.bArmBroken)
    {
        if (Sword && ToImpact > 0 && Distance <= 255.f)
        {
            if (Hero.SuccessfulParries > 0 && Knight.ArmHealth <= 40.f && Distance < 123.f && ToImpact > .34f)
            {
                if (Hero.bOathReady) Hero.TryOathCut(); else Hero.TryAttack();
            }
            else if (ToImpact <= .155f && ToImpact > .065f) Hero.TryParry();
            return;
        }
        if ((Bash || Stomp) && ToImpact > 0 && Distance < (Stomp ? 321.f : 180.f))
        {
            if (ToImpact <= .20f && ToImpact > .085f && Hero.Action == ESBHeroAction::Ready)
            {
                const FVector ToCenter = -Hero.GetActorLocation();
                const FVector Roll = FVector::DotProduct(Flank,ToCenter.GetSafeNormal2D()) < -.2f ? -Flank : Flank;
                MoveToward(Hero, Hero.GetActorLocation()+Roll*350.f, 1.f);
                Hero.TryDodge();
            }
            return;
        }
        if (Distance < 125.f)
        {
            if (Hero.bOathReady) Hero.TryOathCut();
            else if (Hero.Stamina > 36.f || Hero.Action == ESBHeroAction::Cut) Hero.TryAttack();
        }
        return;
    }
    if (Bash && ToImpact > 0 && Distance < 183.f)
    {
        // Orbit inside shield range. The knight tracks for only the first 60% of the tell.
        const FVector Radial = (Hero.GetActorLocation() - Knight.GetActorLocation()).GetSafeNormal2D();
        const FVector Tangent = FVector::CrossProduct(FVector::UpVector, Radial);
        MoveToward(Hero, Hero.GetActorLocation() + Tangent*240.f - Radial*(Distance-78.f)*2.5f, 1.f);
        return;
    }
    if (Stomp && ToImpact > 0 && Distance < 321.f)
    {
        if (ToImpact <= .20f && ToImpact > .085f && Hero.Action == ESBHeroAction::Ready)
        {
            // Roll through the outer edge then close in again.
            const FVector Radial = (Hero.GetActorLocation()-Knight.GetActorLocation()).GetSafeNormal2D();
            MoveToward(Hero, Hero.GetActorLocation()+Radial*350.f, 1.f);
            Hero.TryDodge();
        }
        return;
    }
    if (Distance > 130.f || !Knight.bEncounterActive) return;
    const float RecoveryLeft = Bash ? Knight.CombatData->Bash.Duration()-Knight.PatternElapsed :
        Stomp ? Knight.CombatData->Stomp.Duration()-Knight.PatternElapsed :
        Sword ? Knight.CombatData->Sweep.Duration()-Knight.PatternElapsed : 2.f;
    if (Hero.bOathReady && RecoveryLeft > .58f) Hero.TryOathCut();
    else if (RecoveryLeft > .52f && Hero.Stamina > 40.f)
        Hero.TryAttack();

}

void ASBReviewDriver::Capture(const ASBGameMode& Game, const ASBHero& Hero, const ASBKnight& Knight)
{
    FString Event;
    if (Session.Frame == 0) Event = TEXT("approach");
    if (Game.Encounter==ESBEncounter::Fighting && LastPhase != Knight.Phase) { Event = Knight.Phase==1 ? TEXT("engaged") : TEXT("phase2"); LastPhase=Knight.Phase; }
    if (Hero.SuccessfulParries > LastParries) { Event = TEXT("parry"); LastParries=Hero.SuccessfulParries; }
    if (FMath::RoundToInt(Knight.Health) != LastBossHP) { if (Event.IsEmpty()) Event=TEXT("swordhit"); LastBossHP=FMath::RoundToInt(Knight.Health); }
    if (Knight.bArmBroken && !bLastBroken) { Event=TEXT("armbreak"); bLastBroken=true; }
    if (Knight.Action==ESBKnightAction::Stomp && Knight.PatternElapsed > .42 && LastPatternGeneration != Knight.AttackGeneration)
    { Event=TEXT("stomp"); LastPatternGeneration=Knight.AttackGeneration; }
    if (!bResultSeen && (Game.Encounter == ESBEncounter::Victory || Game.Encounter == ESBEncounter::Defeat))
    { Event=Game.Encounter==ESBEncounter::Victory ? TEXT("victory") : TEXT("defeat"); bResultSeen=true; }
    if (!Event.IsEmpty())
        Append(OutputDirectory / TEXT("events.csv"), FString::Printf(TEXT("%.3f,%d,%d,%s,%.1f,%.1f,%.1f"),
            Session.Elapsed, Session.Frame, Session.Attempt, *Event, Hero.Health, Knight.Health, Knight.ArmHealth));
    if (bVideo)
        FScreenshotRequest::RequestScreenshot(OutputDirectory / FString::Printf(TEXT("Frames/frame_%05d.png"),Session.Frame),false,false);
    else if (!Event.IsEmpty() || Session.Elapsed >= Session.NextSnapshot)
    {
        if (Event.IsEmpty()) Event=TEXT("fight");
        FScreenshotRequest::RequestScreenshot(OutputDirectory / FString::Printf(TEXT("%05d_%s.png"),Session.Frame,*Event),false,false);
        Session.NextSnapshot=Session.Elapsed+8.;
    }
    ++Session.Frame;
}

void ASBReviewDriver::Measure(double Now, float WallFrameMs, ASBKnight& Knight)
{
    if (Knight.Phase != 2) return;
    if (SampleWindow == 0) { SampleWindow = Now; FrameTimes.Reserve(18000); return; }
    if (SampleIndex==0)
    {
        if (Now-SampleWindow >=10.) { SampleWindow = Now; SampleIndex=1; }
        return;
    }
    FrameTimes.Add(WallFrameMs);
    const double Duration = Now-SampleWindow;
    if (Duration<60.) return;
    const int32 Count = FrameTimes.Num();
    FString Samples=TEXT("frame,ms\n");
    for (int32 I=0;I<Count;++I) Samples+=FString::Printf(TEXT("%d,%.4f\n"),I+1,FrameTimes[I]);
    FFileHelper::SaveStringToFile(Samples,*(OutputDirectory / FString::Printf(TEXT("run_%d.csv"),SampleIndex)),
        FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
    FrameTimes.Sort();
    const float P95=FrameTimes[FMath::CeilToInt(Count*.95)-1];
    const FIntPoint View=GEngine && GEngine->GameViewport && GEngine->GameViewport->Viewport
        ? GEngine->GameViewport->Viewport->GetSizeXY() : FIntPoint::ZeroValue;
    Append(OutputDirectory / TEXT("summary.csv"),FString::Printf(TEXT("%d,%.3f,%d,%.3f,%d,%d"),
        SampleIndex,Duration,Count,P95,View.X,View.Y));
    UE_LOG(LogTemp,Display,TEXT("SoulBreak performance run %d p95 %.3f ms (%d frames)"),SampleIndex,P95,Count);
    FrameTimes.Reset(); SampleWindow=FPlatformTime::Seconds(); PreviousFrame=SampleWindow;
    if (++SampleIndex>3) Finish();
}

void ASBReviewDriver::Finish()
{
    if (Session.AudioStarted)
    {
        UAudioMixerBlueprintLibrary::StopRecordingOutput(this,EAudioRecordingExportType::WavFile,TEXT("game"),OutputDirectory);
        Session.AudioStarted=false;
    }
    bFinishing=true;
    SampleWindow=FPlatformTime::Seconds();
    UE_LOG(LogTemp,Display,TEXT("SoulBreak review saved to %s"),*OutputDirectory);
}
#endif
