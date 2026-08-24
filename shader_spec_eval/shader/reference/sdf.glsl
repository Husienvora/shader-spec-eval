void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = (fragCoord - 0.5 * iResolution.xy) / min(iResolution.x, iResolution.y);
    float d = length(uv) - 0.30;            // signed distance to the circle
    float inside = step(d, 0.0);            // hard edge, no smoothstep
    vec3 col = mix(vec3(0.02), vec3(1.0, 0.55, 0.08), inside);
    fragColor = vec4(col, 1.0);
}
