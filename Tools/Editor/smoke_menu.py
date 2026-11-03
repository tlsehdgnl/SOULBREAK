"""Offscreen PIE integration smoke: route real key bindings and widget delegates."""
import json
import os
import time
import traceback
from pathlib import Path
import unreal as u
out=Path(os.getenv('SB_MENU_QA',str(Path(u.Paths.convert_relative_path_to_full(u.Paths.project_saved_dir()))/'MenuQA')))
out.mkdir(parents=True,exist_ok=True)
levels=u.get_editor_subsystem(u.LevelEditorSubsystem)
engine=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if not levels.is_in_play_in_editor() and '/Game/SoulBreak/Maps/L_Cathedral' not in engine.get_editor_world().get_path_name():
    assert levels.load_level('/Game/SoulBreak/Maps/L_Cathedral')
overlay_type=u.load_class(None,'/Game/SoulBreak/UI/WBP_Combat.WBP_Combat_C')
assert overlay_type is not None
if not levels.is_in_play_in_editor():levels.editor_request_begin_play()
u.EditorPythonScripting.set_keep_python_script_alive(True)
state={'step':0,'deadline':time.monotonic()+36,'after':time.monotonic()+4.,'events':[],'end':False}
def note(text):
    state['events'].append(text)
    u.log('SB_MENU_TEST '+text)
def progress(text,delay=.20):
    note(text);state['step']+=1;state['after']=time.monotonic()+delay;state['deadline']=time.monotonic()+20
def end(passed,why=''):
    state['end']=True
    note('PASS' if passed else 'FAIL '+why)
    (out/'report.json').write_text(json.dumps({'passed':passed,'message':why,'events':state['events']},indent=2,ensure_ascii=False))
    u.unregister_slate_post_tick_callback(cb)
    if levels.is_in_play_in_editor(): levels.editor_request_end_play()
    u.EditorPythonScripting.set_keep_python_script_alive(False)
def key(w,k,down=True):u.SystemLibrary.execute_console_command(w,'Input.'+('+' if down else '-')+'key '+k+(' 1' if down else ''))
def press_once(w,k):
    key(w,k)
    def release(dt):
        key(w,k,False)
        u.unregister_slate_post_tick_callback(handle[0])
    handle=[u.register_slate_post_tick_callback(release)]

def overlay(w):
    widgets=u.WidgetLibrary.get_all_widgets_of_class(w,overlay_type,True)
    return widgets[0] if widgets else None
def buttons(widget):
    desc=widget.get_path_name()
    return {str(b.get_content().get_text()):b for b in u.ObjectIterator(u.Button)
            if b.get_path_name().startswith(desc) and b.get_parent() and b.get_content()}
def tick(dt):
    now=time.monotonic()
    if state['end'] or now<state['after']:return
    try:
        if now>state['deadline']:raise RuntimeError('timed out at step '+str(state['step']))
        w=engine.get_game_world()
        if not w or not levels.is_in_play_in_editor():return
        hero=u.GameplayStatics.get_player_pawn(w,0)
        if not hero or not isinstance(hero,u.SBHero):return
        pc=u.GameplayStatics.get_player_controller(w,0)
        paused=u.GameplayStatics.is_game_paused(w);step=state['step']
        if step==0:
            if not hero.get_controller():return
            u.SystemLibrary.execute_console_command(w,'DisableAllScreenMessages')
            press_once(w,'F1');progress('pressed F1 in game')
        elif step==1 and paused:
            widget=overlay(w);assert widget and widget.is_visible()
            acts=buttons(widget);assert len(acts)==3,repr(acts)
            progress('pause visible with '+', '.join(acts),1.)
        elif step==2:
            acts=buttons(overlay(w))
            next(b for caption,b in acts.items() if '계속' in caption).on_clicked.broadcast()
            progress('activated Resume button')
        elif step==3 and not paused:
            assert not overlay(w).is_visible()
            assert not pc.get_editor_property('show_mouse_cursor')
            hero.receive_pattern(24.,False)
            assert hero.get_editor_property('health')<100
            press_once(w,'F1');progress('control restored, injured player, pressed F1')
        elif step==4 and paused:
            next(b for caption,b in buttons(overlay(w)).items() if '재도전' in caption).on_clicked.broadcast()
            progress('activated Retry button')
        elif step==5 and not paused and hero.get_editor_property('health')==100:
            assert abs(hero.get_actor_location().x+800)<150
            assert not pc.get_editor_property('show_mouse_cursor')
            progress('fresh hero at spawn, full HP and cursor captured',1.)
        elif step==6:
            end(True)
    except Exception:
        end(False,traceback.format_exc())
cb=u.register_slate_post_tick_callback(tick)
