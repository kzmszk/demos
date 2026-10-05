"""Read-only resource guard for one rendering job. Never adjusts hardware settings."""
import subprocess,time,sys,pathlib,json,signal,os,datetime
ROOT=pathlib.Path(__file__).resolve().parents[1]
(ROOT/'logs').mkdir(parents=True, exist_ok=True)
def sample():
    p=subprocess.run(['nvidia-smi','--query-gpu=temperature.gpu,power.draw,power.limit,memory.used,memory.total,utilization.gpu','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=8)
    if p.returncode:raise RuntimeError(p.stderr or p.stdout)
    return [float(x) for x in p.stdout.strip().splitlines()[0].split(',')]
initial=sample()
if initial[0]>=76 or initial[2]>200.5:raise SystemExit('GPU temperature/power-limit preflight blocked; no settings changed')
cmd=sys.argv[1:]
p=subprocess.Popen(cmd,start_new_session=True)
def stop(sig=None,frm=None):
    if p.poll() is None:os.killpg(p.pid,signal.SIGTERM)
signal.signal(signal.SIGINT,stop);signal.signal(signal.SIGTERM,stop)
try:
    while p.poll() is None:
        v=sample();entry={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pid':p.pid,'temperature_c':v[0],'power_w':v[1],'power_limit_w':v[2],'vram_mib':v[3],'utilization':v[5]}
        with (ROOT/'logs/thermal.jsonl').open('a') as f:f.write(json.dumps(entry)+'\n')
        if v[0]>=78 or v[3]>v[4]*.92 or v[2]>200.5:
            stop();raise RuntimeError('Thermal/resource guard stopped its child job')
        time.sleep(4)
    sys.exit(p.returncode)
finally:
    stop()
