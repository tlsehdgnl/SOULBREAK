#include "UI/SBCombatHUD.h"
#include "Core/SBGameMode.h"
#include "Combat/SBTrainingDummy.h"
#include "Player/SBHero.h"
#include "Boss/SBKnight.h"
#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "Engine/Font.h"
#include "CanvasItem.h"
#include "GlobalRenderResources.h"

namespace
{
const FLinearColor Ink(.008f,.013f,.021f,.84f);
const FLinearColor Clear(.008f,.013f,.021f,0.f);
const FLinearColor Paper(.94f,.91f,.80f,1);
const FLinearColor Gold(.88f,.65f,.30f,1);
const FLinearColor Muted(.69f,.75f,.74f,1);
const FLinearColor Aqua(.24f,.79f,.76f,1);
const FLinearColor Blood(.79f,.18f,.16f,1);
}

void ASBCombatHUD::Box(float X,float Y,float Width,float Height,FLinearColor Color)
{
    DrawRect(Color, X*Unit,Y*Unit,Width*Unit,Height*Unit);
}
void ASBCombatHUD::Line(float X,float Y,float X2,float Y2,FLinearColor Color,float Weight)
{
    DrawLine(X*Unit,Y*Unit,X2*Unit,Y2*Unit,Color,Weight*Unit);
}
void ASBCombatHUD::Label(const FString& Text,float X,float Y,float Size,FLinearColor Color,bool Center)
{
    UFont* Typeface=GEngine->GetLargeFont();
    if (!Typeface || Text.IsEmpty()) return;
    const FSlateFontInfo Font(Typeface,FMath::Max(6.f,Size*Unit*.76f),Size>=23.f ? TEXT("Bold") : TEXT("Regular"));
    FCanvasTextItem Item(FVector2D(X*Unit,Y*Unit),FText::FromString(Text),Font,Color);
    Item.bCentreX = Center;
    Item.EnableShadow(FLinearColor(0,0,0,.9f),FVector2D(Unit,Unit));
    Canvas->DrawItem(Item);
}
void ASBCombatHUD::Wash(float X,float Y,float Width,float Height,FLinearColor Left,FLinearColor Right)
{
    FCanvasUVTri Upper, Lower;
    const FVector2D TL(X*Unit,Y*Unit), TR((X+Width)*Unit,Y*Unit);
    const FVector2D BL(X*Unit,(Y+Height)*Unit), BR((X+Width)*Unit,(Y+Height)*Unit);
    Upper.V0_Pos=TL; Upper.V1_Pos=TR; Upper.V2_Pos=BL;
    Upper.V0_Color=Left; Upper.V1_Color=Right; Upper.V2_Color=Left;
    Lower.V0_Pos=TR; Lower.V1_Pos=BR; Lower.V2_Pos=BL;
    Lower.V0_Color=Right; Lower.V1_Color=Right; Lower.V2_Color=Left;
    Upper.V0_UV=Upper.V1_UV=Upper.V2_UV=FVector2D::ZeroVector;
    Lower.V0_UV=Lower.V1_UV=Lower.V2_UV=FVector2D::ZeroVector;
    FCanvasTriangleItem Panel(Upper,GWhiteTexture);
    Panel.TriangleList.Add(Lower);
    Panel.BlendMode=SE_BLEND_Translucent;
    Canvas->DrawItem(Panel);
}
void ASBCombatHUD::Sigil(float X,float Y,float Radius,FLinearColor Color)
{
    Diamond(X,Y,Radius,Color);
    Diamond(X,Y,Radius-4,FLinearColor(Color.R,Color.G,Color.B,.44f));
    Line(X,Y-Radius*.72f,X+2,Y-2,Paper,2);
    Line(X-2,Y+1,X,Y+Radius*.68f,Color,2);
    Line(X-5,Y+4,X+5,Y+4,Color);
}
void ASBCombatHUD::Diamond(float X,float Y,float R,FLinearColor Color)
{
    Line(X-R,Y,X,Y-R,Color); Line(X,Y-R,X+R,Y,Color);
    Line(X+R,Y,X,Y+R,Color); Line(X,Y+R,X-R,Y,Color);
}
void ASBCombatHUD::Meter(float X,float Y,float Width,float Height,float Value,float Max,FLinearColor Color)
{
    Box(X-1,Y-1,Width+2,Height+2,FLinearColor(.025f,.028f,.034f,.94f));
    Box(X,Y,Width,Height,FLinearColor(.13f,.13f,.14f,.98f));
    const float Filled = Width*FMath::Clamp(Value/Max,0.f,1.f);
    Box(X,Y,Filled,Height,Color);
    if (Filled > 2) Box(X+Filled-2,Y,2,Height,Paper);
}
void ASBCombatHUD::DrawHUD()
{
    Super::DrawHUD();
    if (!Canvas) return;
    const ASBGameMode* Game = GetWorld()->GetAuthGameMode<ASBGameMode>();
    if (!Game || !Game->Hero || !Game->Knight) return;
    Unit = FMath::Max(.2f,FMath::Min(Canvas->ClipX/1280.f,Canvas->ClipY/720.f));
    W = Canvas->ClipX/Unit; H = Canvas->ClipY/Unit;
    if (Game->bHelpOpen) { Guide(); return; }
    if (Game->Encounter == ESBEncounter::Victory || Game->Encounter == ESBEncounter::Defeat)
    {
        Result(*Game); return;
    }
    Vitals(*Game);
    if (Game->Encounter == ESBEncounter::Fighting) Encounter(*Game);
    else
    {
        FVector2D Pt;
        if (Game->Dummy && PlayerOwner->ProjectWorldLocationToScreen(Game->Dummy->GetActorLocation()+FVector(0,0,204),Pt))
        {
            float X=Pt.X/Unit,Y=Pt.Y/Unit;
            if (X>50 && X<W-50 && Y>32 && Y<H-120)
            {
                Box(X-56,Y-3,112,32,Ink);
                Label(FString::Printf(TEXT("훈련 표적   %d"),FMath::CeilToInt(Game->Dummy->Health)),X,Y,15,Paper,true);
                Meter(X-43,Y+21,86,3,Game->Dummy->Health,100,Gold);
            }
        }
        Wash(26,26,350,100,Ink,Clear);
        Sigil(51,67,15,Gold);
        Label(TEXT("S O U L   B R E A K     /     I"),78,32,14,Gold);
        Label(TEXT("잿빛 대성당"),76,50,29,Paper);
        Line(78,88,219,88,FLinearColor(.66,.48,.23,.62));
        Label(TEXT("성당 안쪽으로 들어가 기사에게 도전하세요"),78,96,15,Muted);
        Wash(W-343,H-107,319,79,Clear,Ink);
        Label(TEXT("좌클릭  베기    우클릭  패링"),W-303,H-99,16,Paper);
        Label(TEXT("Space  회피    Tab  고정    F1  조작"),W-303,H-73,16,Paper);
        Label(TEXT("WASD  이동    마우스  시점"),W-303,H-48,14,Gold);
    }
}
void ASBCombatHUD::Vitals(const ASBGameMode& Game)
{
    const float Y=H-88;
    Wash(22,Y-3,314,64,Ink,Clear);
    Sigil(54,Y+30,20,Game.Hero->bOathReady ? Aqua : Gold);
    Label(TEXT("순례자"),85,Y-1,18,Paper);
    Label(FString::Printf(TEXT("%d"),FMath::CeilToInt(Game.Hero->Health)),268,Y+1,15,Paper);
    Meter(85,Y+27,204,8,Game.Hero->Health,100,Blood);
    const bool bLow=Game.Hero->IsStaminaWarningActive();
    Meter(85,Y+42,204,4,Game.Hero->Stamina,100,bLow ? Gold : Aqua);
    const TCHAR* Pending=nullptr;
    switch (Game.Hero->GetBufferedAction())
    {
    case ESBHeroAction::Cut:
    case ESBHeroAction::ReturnCut: Pending=TEXT("연계 준비"); break;
    case ESBHeroAction::Evade: Pending=TEXT("회피 준비"); break;
    case ESBHeroAction::Parry: Pending=TEXT("패링 준비"); break;
    case ESBHeroAction::OathCut: Pending=TEXT("서약 준비"); break;
    default: break;
    }
    if (Pending || bLow) Label(bLow ? TEXT("스태미나 부족") : Pending,157,Y+1,14,bLow ? Gold : Aqua);
    Line(84,Y+24,289,Y+24,FLinearColor(.66,.51,.29,.62));
    for (int I=1;I<4;++I) Box(85+51*I,Y+27,1,8,FLinearColor(0,0,0,.5));
}
void ASBCombatHUD::Encounter(const ASBGameMode& Game)
{
    const ASBKnight& Boss = *Game.Knight;
    const float C = W*.5f;
    Wash(C-288,16,288,90,Clear,Ink);
    Wash(C,16,288,90,Ink,Clear);
    Label(Boss.Phase==1 ? TEXT("Ⅰ    칼날의 맹세") : TEXT("Ⅱ    무너진 서약"),C,22,15,Gold,true);
    Label(TEXT("잿빛 성당의 기사"),C,42,25,Paper,true);
    const float Now=GetWorld()->GetTimeSeconds();
    if (Boss.Health<PreviousBossHP)
    {
        TrailingBossHP=FMath::Max(TrailingBossHP,PreviousBossHP);
        DamageHoldUntil=Now+.16f;
    }
    PreviousBossHP=Boss.Health;
    if (Now>=DamageHoldUntil)
        TrailingBossHP=FMath::FInterpConstantTo(TrailingBossHP,Boss.Health,GetWorld()->GetDeltaSeconds(),160.f);
    Meter(C-225,78,450,7,TrailingBossHP,400,Gold);
    Box(C-225,78,450*FMath::Clamp(Boss.Health/400.f,0.f,1.f),7,Blood);
    Box(C-1,78,2,7,FLinearColor(.02,.025,.034,.72));
    Diamond(C-234,81,4,Gold); Diamond(C+234,81,4,Gold);
    Wash(W-219,29,189,58,Clear,Ink);
    Label(Boss.bArmBroken ? TEXT("오른팔  /  파괴됨") : TEXT("오른팔  /  검 갑주"),W-187,35,16,Boss.bArmBroken ? Gold : Paper);
    Meter(W-185,65,139,4,Boss.ArmHealth,90,Gold);
    if (Boss.bArmBroken && !bSawBreak)
    {
        bSawBreak=true; ArmNoticeUntil=GetWorld()->GetTimeSeconds()+2.3f;
    }
    if (GetWorld()->GetTimeSeconds()<ArmNoticeUntil)
    {
        Wash(C-160,H*.26f,160,58,Clear,Ink);
        Wash(C,H*.26f,160,58,Ink,Clear);
        Label(TEXT("A R M O R   B R O K E N"),C,H*.26f+5,15,Gold,true);
        Label(TEXT("검을 든 오른팔 파괴"),C,H*.26f+25,21,Paper,true);
    }
    if (Boss.TelegraphDuration > 0 && Boss.PatternElapsed < Boss.TelegraphDuration && !Boss.PatternLabel.IsEmpty())
    {
        Wash(C-130,H-100,130,47,Clear,Ink);
        Wash(C,H-100,130,47,Ink,Clear);
        Label(Boss.PatternLabel,C,H-95,19,Paper,true);
        Meter(C-90,H-64,180,4,Boss.PatternElapsed,Boss.TelegraphDuration,Gold);
    }
    if (Game.Hero->bLockedOn)
    {
        FVector2D Pt;
        if (PlayerOwner->ProjectWorldLocationToScreen(Boss.GetActorLocation()+FVector(0,0,32),Pt))
            Diamond(Pt.X/Unit,Pt.Y/Unit,7,Paper);
        if (!Boss.bArmBroken && Game.Hero->GetDistanceTo(Game.Knight)<340 &&
            PlayerOwner->ProjectWorldLocationToScreen(Boss.ArmPoint(),Pt))
        {
            float X=Pt.X/Unit,Y=Pt.Y/Unit;
            Line(X-8,Y-2,X-4,Y-6,Gold,1.5f); Line(X+4,Y+6,X+8,Y+2,Gold,1.5f);
        }
    }
    if (Game.Hero->bOathReady)
    {
        Wash(30,H-126,215,31,Ink,Clear);
        Diamond(48,H-111,6,Aqua);
        Label(TEXT("E   서약 절단 준비"),65,H-124,19,Aqua);
    }
    if (Game.Hero->ParryPulse > 0) Label(TEXT("완벽한 패링"),C,H*.60f,24,Aqua,true);
    if (Game.Hero->HitPulse > 0)
    {
        const FLinearColor Red(.65f,.03f,.02f,.52f*Game.Hero->HitPulse);
        Box(0,0,W,5,Red); Box(0,H-5,W,5,Red);
    }
    Label(TEXT("F1   조작"),W-102,H-52,15,Muted);
}
void ASBCombatHUD::Guide()
{
    Box(0,0,W,H,FLinearColor(.008f,.013f,.019f,.85f));
    const float X=W*.5f-204, Y=H*.5f-198;
    Line(X,Y,X+408,Y,Gold);
    Label(TEXT("S O U L   B R E A K     /     P A U S E"),X,Y+15,16,Gold);
    Label(TEXT("순례자의 전투 수첩"),X,Y+46,34,Paper);
    const TCHAR* Keys[]={TEXT("W A S D  /  마우스"),TEXT("Shift  /  Space"),TEXT("좌클릭  ×  2"),TEXT("우클릭"),TEXT("Tab  /  E")};
    const TCHAR* Acts[]={TEXT("이동  /  시점"),TEXT("달리기  /  회피"),TEXT("검 베기  /  연계 공격"),TEXT("패링  ·  검이 닿기 직전에"),TEXT("기사 고정  /  패링 후 서약 절단")};
    for (int32 I=0;I<5;++I)
    {
        const float Row=Y+109+I*34;
        Label(Keys[I],X,Row,18,Gold); Label(Acts[I],X+180,Row,18,Paper);
    }
    Label(TEXT("베기가 끝나면 회피나 패링으로 바로 전환할 수 있습니다."),X,Y+292,17,Muted);
    Line(X,Y+338,X+408,Y+338,Gold);
    Label(TEXT("Esc / F1   계속      R   재도전      Q   종료"),X,Y+356,17,Paper);
}
void ASBCombatHUD::Result(const ASBGameMode& Game)
{
    const bool Win = Game.Encounter==ESBEncounter::Victory;
    const float Fade=FMath::Clamp(Game.OutcomeSeconds*1.4f,0.f,1.f);
    Box(0,0,W,H,FLinearColor(.006f,.01f,.015f,Fade*.6f));
    if (Fade<.25f) return;
    const float C=W*.5f,Y=H*.35f;
    Box(C-235,Y-22,470,229,Ink);
    Line(C-210,Y-1,C-18,Y-1,Gold); Diamond(C,Y-1,7,Gold); Line(C+18,Y-1,C+210,Y-1,Gold);
    Label(Win ? TEXT("O A T H   S E V E R E D") : TEXT("P I L G R I M   F A L L E N"),C,Y+15,17,Gold,true);
    Label(Win ? TEXT("기사의 맹세를 끊었다") : TEXT("순례자가 쓰러졌다"),C,Y+45,36,Paper,true);
    const int32 Sec=FMath::FloorToInt(Game.FightSeconds);
    Label(FString::Printf(TEXT("%02d:%02d     /     오른팔 %s"),Sec/60,Sec%60,Game.Knight->bArmBroken ? TEXT("파괴") : TEXT("온전")),C,Y+105,17,Muted,true);
    Label(TEXT("R   다시 도전      Q   게임 종료"),C,Y+156,20,Gold,true);
}
