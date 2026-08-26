void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = fragCoord / iResolution.xy;
    float cell = mod(floor(uv.x * 6.0) + floor(uv.y * 4.0), 2.0);
    fragColor = vec4(mix(vec3(0.015), vec3(1.0, 0.9, 0.05), cell), 1.0);
}
