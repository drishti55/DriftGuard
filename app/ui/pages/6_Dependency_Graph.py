import streamlit as st
import pandas as pd
import networkx as nx
import plotly.graph_objects as go
from pathlib import Path

st.title("🕸️ Repository Relationship & Dependency Graph")
st.markdown("Visual mapping of verified cross-artifact relationships and drift candidates.")

if not st.session_state.get("repo_info"):
    st.warning("Please load a repository in the Overview page first.")
    st.stop()

info = st.session_state.repo_info
# drift_candidates is a list of candidate dicts produced by RepositoryScanner.scan().
# Use getattr so this page does not crash if an older RepoInfo is somehow in session state.
candidates = getattr(info, 'drift_candidates', [])
metrics = getattr(info, 'scan_metrics', {}) or {}

G = nx.Graph()

# Add relevant nodes only
for a in getattr(info, 'artifacts', []):
    if getattr(a, 'status', 'RELEVANT') == "RELEVANT":
        G.add_node(a.path, type=a.artifact_category)

# Add real relationship edges from candidates
for c in candidates:
    p1 = c["artifact_1"]["path"]
    p2 = c["artifact_2"]["path"]
    rel = c.get("relationship_type", "related")
    if p1 in G and p2 in G:
        G.add_edge(p1, p2, rel=rel)

c1, c2, c3 = st.columns(3)
with c1:
    st.metric("Relevant Artifact Nodes", G.number_of_nodes())
with c2:
    st.metric("Verified Cross-Domain Edges", G.number_of_edges())
with c3:
    # Use scan_metrics as the authoritative source; fallback to len(candidates)
    v = metrics.get("candidates_generated", len(candidates))
    st.metric("Drift Candidates", v)

if G.number_of_edges() > 0:
    st.info("Interactive visualization of cross-artifact relationships:")

    # If graph is very large, visualize the subgraph of nodes with highest degree for clarity
    display_graph = G
    if G.number_of_nodes() > 100:
        top_nodes = sorted(G.nodes(), key=lambda n: G.degree(n), reverse=True)[:100]
        display_graph = G.subgraph(top_nodes)
        st.caption(f"Visualizing top 100 most connected artifact nodes out of {G.number_of_nodes()} total.")

    pos = nx.spring_layout(display_graph, seed=42)
    edge_x = []
    edge_y = []
    for edge in display_graph.edges():
        if edge[0] in pos and edge[1] in pos:
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=1, color='#888'),
        hoverinfo='none',
        mode='lines'
    )

    node_x = []
    node_y = []
    node_text = []
    node_color = []

    color_map = {
        "source_code": "#1f77b4",
        "documentation": "#2ca02c",
        "test": "#ff7f0e",
        "dependency": "#d62728",
        "docker_configuration": "#9467bd",
        "ci_configuration": "#8c564b",
        "deployment_configuration": "#e377c2",
        "build_configuration": "#7f7f7f",
        "other_configuration": "#bcbd22",
    }

    for node in display_graph.nodes():
        if node in pos:
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            ntype = display_graph.nodes[node].get('type', 'other')
            node_text.append(f"{Path(node).name}<br>Type: {ntype}<br>Path: {node}")
            node_color.append(color_map.get(ntype, "#17becf"))

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers',
        hoverinfo='text',
        text=node_text,
        marker=dict(
            showscale=False,
            color=node_color,
            size=10,
            line_width=1
        )
    )

    fig = go.Figure(data=[edge_trace, node_trace],
                 layout=go.Layout(
                    showlegend=False,
                    hovermode='closest',
                    margin=dict(b=0,l=0,r=0,t=0),
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    height=500
                 ))
    st.plotly_chart(fig, use_container_width=True)

# Candidate relationship table
st.subheader("All Generated Drift Candidates")
cand_data = []
for c in candidates:
    cand_data.append({
        "Type": c.get("relationship_type", "").replace("_", " ").title(),
        "Artifact 1": c["artifact_1"]["path"],
        "Artifact 2": c["artifact_2"]["path"],
        "Rationale": c.get("rationale", "")
    })

st.dataframe(pd.DataFrame(cand_data), use_container_width=True)
