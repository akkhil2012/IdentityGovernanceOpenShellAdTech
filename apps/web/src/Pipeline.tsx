import {useEffect, useRef} from 'react';

type Stage = {agent: string; status: string; sandbox_id: string; governance: string; reason?: string};
type D3Api = {select: (target: SVGSVGElement) => any; line: () => any; curveBumpX: unknown};

declare global { interface Window { d3?: D3Api } }

const colors: Record<string, string> = {ok: '#70e3ad', denied: '#ff776d', idle: '#52605a'};

export function Pipeline({stages}: {stages: Stage[]}) {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    const svgNode = svgRef.current;
    if (!svgNode) return;

    const draw = () => {
      const d3 = window.d3;
      if (!d3) return;
      const width = Math.max(svgNode.parentElement?.clientWidth || 800, 320);
      const compact = width < 720;
      const height = compact ? stages.length * 116 + 24 : 222;
      const svg = d3.select(svgNode);
      svg.selectAll('*').remove();
      svg.attr('viewBox', `0 0 ${width} ${height}`);
      svg.append('title').text('Governed agent execution pipeline');
      svg.append('desc').text(stages.map(stage => `${stage.agent}: ${stage.status}`).join(', '));

      const points = stages.map((stage, index) => ({...stage, index,
        x: compact ? 42 : 60 + index * ((width - 120) / Math.max(stages.length - 1, 1)),
        y: compact ? 62 + index * 116 : 76,
      }));
      const defs = svg.append('defs');
      for (const [status, color] of Object.entries(colors)) {
        defs.append('marker').attr('id', `pipeline-arrow-${status}`).attr('viewBox', '0 -5 10 10')
          .attr('refX', 8).attr('markerWidth', 6).attr('markerHeight', 6).attr('orient', 'auto')
          .append('path').attr('d', 'M0,-5L10,0L0,5').attr('fill', color);
      }

      const connectors = svg.append('g');
      points.slice(0, -1).forEach((point, index) => {
        const next = points[index + 1];
        const status = next.status === 'denied' ? 'denied' : point.status === 'ok' ? 'ok' : 'idle';
        const path = compact ? `M${point.x},${point.y + 27} L${next.x},${next.y - 27}`
          : d3.line().curve(d3.curveBumpX)([[point.x + 28, point.y], [next.x - 28, next.y]]);
        connectors.append('path').attr('d', path).attr('class', `pipeline-connector ${status}`)
          .attr('marker-end', `url(#pipeline-arrow-${status})`);
      });

      const nodes = svg.append('g').selectAll('g').data(points).join('g')
        .attr('class', (stage: Stage) => `pipeline-node ${stage.status}`)
        .attr('transform', (stage: {x: number; y: number}) => `translate(${stage.x},${stage.y})`);
      nodes.append('circle').attr('r', 27);
      nodes.append('circle').attr('class', 'pipeline-node-core').attr('r', 17);
      nodes.append('text').attr('class', 'pipeline-index').attr('text-anchor', 'middle').attr('dy', '0.35em')
        .text((stage: {index: number}) => String(stage.index + 1).padStart(2, '0'));
      nodes.append('text').attr('class', 'pipeline-name').attr('text-anchor', compact ? 'start' : 'middle')
        .attr('x', compact ? 48 : 0).attr('y', compact ? -8 : 49).text((stage: Stage) => stage.agent);
      nodes.append('text').attr('class', 'pipeline-state').attr('text-anchor', compact ? 'start' : 'middle')
        .attr('x', compact ? 48 : 0).attr('y', compact ? 12 : 67).text((stage: Stage) => stage.governance);
      nodes.append('text').attr('class', 'pipeline-sandbox').attr('text-anchor', compact ? 'start' : 'middle')
        .attr('x', compact ? 48 : 0).attr('y', compact ? 31 : 87).text((stage: Stage) => stage.sandbox_id);

      const denied = points.find(stage => stage.reason);
      if (denied && !compact) svg.append('text').attr('class', 'pipeline-reason').attr('x', denied.x)
        .attr('y', 190).attr('text-anchor', 'middle').text(denied.reason);
    };

    const d3Script = document.querySelector<HTMLScriptElement>('script[data-d3]');
    d3Script?.addEventListener('load', draw);
    const observer = new ResizeObserver(draw);
    observer.observe(svgNode.parentElement || svgNode);
    draw();
    return () => { d3Script?.removeEventListener('load', draw); observer.disconnect(); };
  }, [stages]);

  return <div className="pipeline" aria-live="polite"><svg ref={svgRef} role="img" preserveAspectRatio="xMidYMid meet" />
    <ol className="sr-only">{stages.map(stage => <li key={stage.agent}>{stage.agent}: {stage.governance}, {stage.status}{stage.reason ? `. ${stage.reason}` : ''}</li>)}</ol>
  </div>;
}
