<!--
	UmlMarkerDefs: SVG marker definitions for UML edge arrowheads (ADR-086).
	Must be rendered inside <SvelteFlow> so markers share the same SVG context.
-->
<svg style="position: absolute; width: 0; height: 0; overflow: hidden;">
	<defs>
		<!-- Filled diamond: composition (source marker) -->
		<marker
			id="uml-diamond-filled"
			markerWidth="18"
			markerHeight="12"
			refX="0"
			refY="6"
			orient="auto"
			markerUnits="userSpaceOnUse"
			overflow="visible"
		>
			<polygon points="0,6 9,0 18,6 9,12" fill="#333" stroke="#333" stroke-width="1" />
		</marker>

		<!-- Open diamond: aggregation (source marker) -->
		<marker
			id="uml-diamond-open"
			markerWidth="18"
			markerHeight="12"
			refX="0"
			refY="6"
			orient="auto"
			markerUnits="userSpaceOnUse"
			overflow="visible"
		>
			<polygon points="0,6 9,0 18,6 9,12" fill="#fff" stroke="#333" stroke-width="1.5" />
		</marker>

		<!-- Closed triangle: generalization/realization (target marker) -->
		<marker
			id="uml-triangle-closed"
			markerWidth="14"
			markerHeight="12"
			refX="14"
			refY="6"
			orient="auto"
			markerUnits="userSpaceOnUse"
			overflow="visible"
		>
			<polygon points="0,0 14,6 0,12" fill="#fff" stroke="#333" stroke-width="1.5" />
		</marker>

		<!-- Open arrow: dependency/usage/association (target marker) -->
		<marker
			id="uml-arrow-open"
			markerWidth="14"
			markerHeight="12"
			refX="14"
			refY="6"
			orient="auto"
			markerUnits="userSpaceOnUse"
			overflow="visible"
		>
			<polyline points="0,0 14,6 0,12" fill="none" stroke="#333" stroke-width="1.5" />
		</marker>
	</defs>
</svg>
