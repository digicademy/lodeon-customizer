variable "CORE_ROOT" {
  default = "../.."
}

group "default" {
  targets = ["customizer"]
}

target "core-wheel" {
  context    = CORE_ROOT
  dockerfile = "api/Dockerfile"
  target     = "model-runtime-wheel"
}

target "customizer" {
  context = "."
  platforms = ["linux/amd64", "linux/arm64"]
  contexts = {
    model_runtime = "target:core-wheel"
    core          = CORE_ROOT
  }
  tags = ["registry.gitlab.rlp.net/adwmainz/digicademy/lodeon/lodeon-customizer:0.1.0"]
}
