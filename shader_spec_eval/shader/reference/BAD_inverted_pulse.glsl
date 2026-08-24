void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = (fragCoord - 0.5 * iResolution.xy) / iResolution.y;
    float r = length(uv);
    float i = clamp(r * (1.2 + 0.25 * sin(iTime * 2.2)), 0.0, 1.0);
    fragColor = vec4(vec3(0.12, 0.30, 1.0) * i, 1.0);
}
