<!--
	UmlMarkerDefs: SVG marker definitions for UML edge arrowheads (ADR-086).
	Must be rendered inside <SvelteFlow> so markers share the same SVG context.
-->
<svg style="position: absolute; width: 0; height: 0; overflow: hidden;">
	<defs>
		<!-- Filled diamond: composition (source marker) -->
		<marker
			id="uml-diamond-filled"
			markerWidth="16"
			markerHeight="10"
			refX="16"
			refY="5"
			orient="auto"
			markerUnits="userSpaceOnUse"
		>
			<polygon points="0,5 8,0 16,5 8,10" fill="#333" stroke="#333" stroke-width="1" />
		</marker>

		<!-- Open diamond: aggregation (source marker) -->
		<marker
			id="uml-diamond-open"
			markerWidth="16"
			markerHeight="10"
			refX="16"
			refY="5"
			orient="auto"
			markerUnits="userSpaceOnUse"
		>
			<polygon points="0,5 8,0 16,5 8,10" fill="#fff" stroke="#333" stroke-width="1.5" />
		</marker>

		<!-- Closed triangle: generalization/realization (target marker) -->
		<marker
			id="uml-triangle-closed"
			markerWidth="14"
			markerHeight="10"
			refX="14"
			refY="5"
			orient="auto"
			markerUnits="userSpaceOnUse"
		>
			<polygon points="0,0 14,5 0,10" fill="#fff" stroke="#333" stroke-width="1.5" />
		</marker>

		<!-- Open arrow: dependency/usage/association (target marker) -->
		<marker
			id="uml-arrow-open"
			markerWidth="12"
			markerHeight="10"
			refX="12"
			refY="5"
			orient="auto"
			markerUnits="userSpaceOnUse"
		>
			<polyline points="0,0 12,5 0,10" fill="none" stroke="#333" stroke-width="1.5" />
		</marker>
	</defs>
</svg>
