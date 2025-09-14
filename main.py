# -*- coding: utf-8 -*-
"""
Actividad 1 – Reto de Algoritmos
Rescate de Datos Críticos en 120 minutos con dependencias y recursos limitados.

Cómo usar:
1) Edita la lista TASKS y RESOURCES con tus datos.
2) Ejecuta:  python main.py
3) Verás el cronograma propuesto, uso de recursos y si cabe en 120 min.

Autor: tú :)
"""

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional

HORIZON_MIN = 120  # Límite de tiempo duro (minutos)

# -----------------------------
# Modelos de datos
# -----------------------------
@dataclass
class Task:
    id: str
    name: str
    duration: int  # en minutos
    requires: Dict[str, int]  # recurso -> cantidad necesaria
    deps: List[str]  # ids de tareas que deben terminar antes

@dataclass
class Resource:
    name: str
    quantity: int  # cuántas unidades disponibles en paralelo

# -----------------------------
# Datos de ejemplo (edítalos)
# -----------------------------
RESOURCES: Dict[str, Resource] = {
    # Ejemplos: técnicos, servidores, canal de comunicación, etc.
    "tecnico": Resource("tecnico", 2),
    "servidor": Resource("servidor", 1),
    "comunicacion": Resource("comunicacion", 1),
}

TASKS: Dict[str, Task] = {
    # 1. Contención y diagnóstico
    "A": Task("A", "Aislar red afectada", 20, {"tecnico": 1}, []),
    "B": Task("B", "Verificar backups disponibles", 15, {"tecnico": 1, "servidor": 1}, ["A"]),
    "C": Task("C", "Análisis de alcance (inventario sistemas críticos)", 20, {"tecnico": 1}, ["A"]),

    # 2. Plan de restauración y prioridades
    "D": Task("D", "Definir prioridades de restauración", 10, {"tecnico": 1}, ["B", "C"]),

    # 3. Restauración de datos críticos
    "E": Task("E", "Montar entorno de restore", 25, {"tecnico": 1, "servidor": 1}, ["D"]),
    "F": Task("F", "Restaurar BD Pacientes", 35, {"tecnico": 1, "servidor": 1}, ["E"]),
    "G": Task("G", "Restaurar Historial Citas", 25, {"tecnico": 1, "servidor": 1}, ["E"]),

    # 4. Verificación y validación
    "H": Task("H", "Pruebas de integridad", 15, {"tecnico": 1}, ["F", "G"]),

    # 5. Comunicación de crisis (se puede hacer en paralelo tras contención)
    "I": Task("I", "Comunicación a dirección y legales", 10, {"comunicacion": 1}, ["A"]),
    "J": Task("J", "Aviso interno a áreas clínicas", 10, {"comunicacion": 1}, ["I"]),
}

# -----------------------------
# Utilidades: Topological sort
# -----------------------------
def topo_sort(tasks: Dict[str, Task]) -> List[str]:
    indeg = {tid: 0 for tid in tasks}
    adj = defaultdict(list)
    for t in tasks.values():
        for d in t.deps:
            adj[d].append(t.id)
            indeg[t.id] += 1
    q = deque([tid for tid, deg in indeg.items() if deg == 0])
    order = []
    while q:
        u = q.popleft()
        order.append(u)
        for v in adj[u]:
            indeg[v] -= 1
            if indeg[v] == 0:
                q.append(v)
    if len(order) != len(tasks):
        raise ValueError("¡Ciclo de dependencias detectado! Revisa 'deps'.")
    return order

# -----------------------------
# Planificador greedy con recursos
# -----------------------------
def schedule(tasks: Dict[str, Task],
             resources: Dict[str, Resource],
             horizon: int = HORIZON_MIN) -> Tuple[Dict[str, Tuple[int, int]], List[str]]:
    """
    Devuelve:
      - plan: dict task_id -> (inicio, fin)
      - warnings: lista de mensajes (por ejemplo, si no cabe en 120 min)
    Estrategia:
      - Avanza minuto a minuto.
      - Inicia tareas cuyas dependencias estén completas y haya recursos suficientes.
      - Libera recursos al terminar cada tarea.
    """
    order = topo_sort(tasks)
    # Estado de recursos: disponibilidad por minuto
    avail = {r: resources[r].quantity for r in resources}
    time = 0
    running: Dict[str, int] = {}  # task_id -> tiempo restante
    plan: Dict[str, Tuple[int, int]] = {}
    done = set()
    ready = set([tid for tid in order if not tasks[tid].deps])
    warnings: List[str] = []

    # Para poder activar tareas cuando sus deps se completen
    dependents = defaultdict(list)
    remaining_deps = {tid: set(tasks[tid].deps) for tid in tasks}
    for t in tasks.values():
        for d in t.deps:
            dependents[d].append(t.id)

    while len(done) < len(tasks) and time <= horizon:
        # 1) Intentar iniciar tareas "ready" que no corren aún
        started_any = True
        while started_any:
            started_any = False
            # Orden determinista: según 'order'
            for tid in order:
                if tid in ready and tid not in running and tid not in done:
                    t = tasks[tid]
                    if all(avail.get(r, 0) >= need for r, need in t.requires.items()):
                        # Reservar recursos
                        for r, need in t.requires.items():
                            avail[r] -= need
                        running[tid] = t.duration
                        plan[tid] = (time, -1)  # fin se fija al terminar
                        started_any = True

        # 2) Avanzar un minuto
        time += 1
        if time > horizon and len(done) < len(tasks):
            break

        # 3) Actualizar tareas en ejecución
        finished_now = []
        for tid in list(running.keys()):
            running[tid] -= 1
            if running[tid] == 0:
                finished_now.append(tid)

        # 4) Cerrar terminadas, liberar recursos y desbloquear dependientes
        for tid in finished_now:
            t = tasks[tid]
            start, _ = plan[tid]
            plan[tid] = (start, time)
            # Liberar recursos
            for r, need in t.requires.items():
                avail[r] += need
            running.pop(tid, None)
            done.add(tid)
            # Desbloquear
            for dep_t in dependents[tid]:
                remaining_deps[dep_t].discard(tid)
                if not remaining_deps[dep_t]:
                    ready.add(dep_t)

        # Las que no han empezado y no tienen deps, mantener en ready
        for tid in order:
            if tid not in done and not remaining_deps[tid]:
                ready.add(tid)

    if len(done) < len(tasks):
        warnings.append(f"No caben todas las tareas en {horizon} minutos. "
                        f"Completadas: {len(done)}/{len(tasks)}. Último tiempo simulado: {time} min.")

    return plan, warnings

# -----------------------------
# Render sencillo (tabla + mini Gantt ASCII)
# -----------------------------
def print_schedule(tasks: Dict[str, Task], plan: Dict[str, Tuple[int, int]]):
    print("\n=== CRONOGRAMA PROPUESTO (minutos desde t=0) ===")
    rows = []
    for tid, (s, e) in sorted(plan.items(), key=lambda kv: (kv[1][0], kv[1][1])):
        t = tasks[tid]
        rows.append((s, e, tid, t.name, t.duration, t.requires))
    print(f"{'Inicio':>6} {'Fin':>6}  {'ID':<4}  {'Tarea':<35} {'Dur.':>4}  Recursos")
    for s, e, tid, name, dur, req in rows:
        print(f"{s:6d} {e:6d}  {tid:<4}  {name:<35} {dur:4d}  {req}")

    # Mini Gantt
    print("\n=== GANTT (cada · = 5 min) ===")
    scale = 5
    for _, (s, e), tid, name, *_ in rows:
        start_blocks = s // scale
        len_blocks = max(1, (e - s) // scale)
        line = "·" * start_blocks + "#" * len_blocks
        print(f"{tid:<4} {line}  {name}")

def main():
    print("Planificando con límite de", HORIZON_MIN, "min…")
    try:
        plan, warnings = schedule(TASKS, RESOURCES, HORIZON_MIN)
    except ValueError as ex:
        print("ERROR:", ex)
        return

    print_schedule(TASKS, plan)

    if warnings:
        print("\n⚠️  ADVERTENCIAS")
        for w in warnings:
            print(" -", w)

    # Métrica rápida
    makespan = max((end for (_, end) in plan.values()), default=0)
    print(f"\nTiempo total (makespan): {makespan} min")
    if makespan <= HORIZON_MIN:
        print("✅ El plan cabe dentro de la ventana de 120 minutos.")
    else:
        print("❌ El plan excede la ventana de 120 minutos.")

if __name__ == "__main__":
    main()
    
