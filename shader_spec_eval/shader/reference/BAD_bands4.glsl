void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    float v = floor(min(fragCoord.x / iResolution.x, 0.999) * 4.0) / 3.0;
    fragColor = vec4(vec3(v), 1.0);
}
