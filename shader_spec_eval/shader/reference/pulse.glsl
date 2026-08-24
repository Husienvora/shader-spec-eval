void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = (fragCoord - 0.5 * iResolution.xy) / iResolution.y;
    float r = length(uv);
    // Pulse radius breathes with time; brightest at centre, dark at corners.
    float pulse = 0.55 + 0.30 * sin(iTime * 2.2);
    float falloff = smoothstep(pulse, 0.0, r);
    float core = exp(-r * r * 7.0);
    float i = clamp(falloff * 0.75 + core * 0.85, 0.0, 1.0);
    vec3 col = vec3(0.12, 0.30, 1.0) * i;
    col += vec3(0.05, 0.10, 0.28) * (1.0 - r);
    fragColor = vec4(col, 1.0);
}
