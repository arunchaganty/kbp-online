/* Visualizations for infobalize */

/* 
 * Creates a graph at @svg using the data in @graph.
 * Assumes @graph contains "nodes" and "edges".
 *  - node attributes include id, type and href.
 *  - edge attributes include source, target, type and weight.
 */
function createGraph(svg, graph) {
  var width = +svg.attr("width"),
      height = +svg.attr("height");

  // Create graphical elements for the graph.
  var nodes = svg.append("g")
    .selectAll("circle")
    .data(graph.nodes)
    .enter()
//    .append("a")
      //.attr("xlink:href", function(d) {return d.href;})
      .append("circle")
        .attr("class", function(d) {return "node " + d.type;})
        .attr("r", 6)
        .call(d3.drag()
            .on("start", dragstarted)
            .on("drag", dragged)
            .on("end", dragended));

  var edges = svg.append("g")
    .selectAll("path")
    .data(graph.edges)
    .enter().append("path")
      .attr("class", function(d) {return "link " + d.type;})
      .attr("stroke-width", function(d) {return d.weight;})
      .attr("marker-end", function(d) {return "url(#" + d.type + ")";});

  var text = svg.append("g")
    .selectAll("text")
    .data(graph.nodes)
    .enter().append("text")
      .attr("x", 8)
      .attr("y", ".51em")
      .text(function(d) {return d.id;});

  var simulation = d3.forceSimulation()
    .force("charge", d3.forceManyBody())
    .force("center", d3.forceCenter(width/2, height/2))
    .force("link", d3.forceLink()
        .distance(100)
        .strength(0.5)
        .id(function(d) {return d.id;}));

  simulation
    .nodes(graph.nodes)
    .on("tick", tick)
    .force("link")
      .links(graph.edges);

  function tick() {
    nodes.attr("transform", function(d) { return "translate(" + d.x + "," + d.y + ")"});
    text.attr("transform", function(d) { return "translate(" + d.x + "," + d.y + ")"});
    edges.attr("d", linkArc); 
   // function(d) {
   //   return "M" + d.source.x + "," + d.target.y
   //        + "S" + d.source.x + "," + d.target.y
   //        + " " + d.source.x + "," + d.target.y;
   // });
  }

  function dragstarted(d) {
    if (!d3.event.active) simulation.alphaTarget(0.3).restart();
    d.fx = d.x;
    d.fy = d.y;
  }

  function dragged(d) {
    d.fx = d3.event.x;
    d.fy = d3.event.y;
  }

  function dragended(d) {
    if (!d3.event.active) simulation.alphaTarget(0);
    d.fx = null;
    d.fy = null;
  }

}

// Use elliptical arc path segments to doubly-encode directionality.
function linkArc(d) {
  var dx = d.target.x - d.source.x,
      dy = d.target.y - d.source.y,
      dr = Math.sqrt(dx * dx + dy * dy);
  return "M" + d.source.x + "," + d.source.y + "A" + dr + "," + dr + " 0 0,1 " + d.target.x + "," + d.target.y;
}

