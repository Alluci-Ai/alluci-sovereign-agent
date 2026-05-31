#include "ppn_model_core.hpp"
#include "ppn_secure_router.hpp"
#include "manifold_distillation.hpp"
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

// Define the PyBind11 Python Module
// "alluci_core" must match the name in CMakeLists.txt pybind11_add_module
PYBIND11_MODULE(alluci_core, m) {
  m.doc() = "Alluci Sovereign Agent Native Apple MLX Core Binding";

  // Bind the Routing Manifest Struct
  py::class_<alluci::CloudRoutingManifest>(m, "CloudRoutingManifest")
      .def_readwrite("clean_abstract_payload", &alluci::CloudRoutingManifest::clean_abstract_payload)
      .def_readwrite("pii_vault_registry", &alluci::CloudRoutingManifest::pii_vault_registry);

  // Bind the Sovereign Router
  py::class_<alluci::AlluciSovereignRouter>(m, "AlluciSovereignRouter")
      .def(py::init<>())
      .def("isolate_personal_perimeter", &alluci::AlluciSovereignRouter::isolate_personal_perimeter, py::arg("raw_user_prompt"))
      .def("deanonymize_response", &alluci::AlluciSovereignRouter::deanonymize_response, py::arg("cloud_response"), py::arg("pii_vault_registry"));

  // Bind VDXF Barcode
  py::class_<alluci::DistilledTopologyBarcode>(m, "DistilledTopologyBarcode")
      .def_readwrite("vdxf_target_domain_key", &alluci::DistilledTopologyBarcode::vdxf_target_domain_key);

  // Bind Manifold Distiller
  py::class_<alluci::ManifoldDistiller>(m, "ManifoldDistiller")
      .def(py::init<>());

  // Bind the C++ class to Python
  py::class_<alluci::AlluciCognitiveEngine>(m, "AlluciCognitiveEngine")
      // Expose the constructor taking the model directory
      .def(py::init<const std::string &>(), py::arg("model_dir"))

      // Expose the dynamic LoRA injection method
      .def("inject_lora_adapters",
           &alluci::AlluciCognitiveEngine::inject_lora_adapters,
           py::arg("lora_path"),
           "Hot-swaps LoRA Polytope adapters from the Dream Cycle into the "
           "neural network")

      // Expose the primary evaluation loop
      .def("evaluate_intent", &alluci::AlluciCognitiveEngine::evaluate_intent,
           py::arg("prompt"), py::arg("max_tokens") = 1024,
           py::arg("temperature") = 0.7f,
           "Executes the prompt on the Apple Silicon Neural Engine");
}
