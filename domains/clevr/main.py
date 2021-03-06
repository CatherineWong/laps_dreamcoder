from dreamcoder.utilities import *
from dreamcoder.recognition import *
from dreamcoder.enumeration import *
from dreamcoder.dreamcoder import ecIterator, default_wake_generative

from dreamcoder.domains.clevr.clevrPrimitives import *
import dreamcoder.domains.clevr.makeClevrTasks as makeClevrTasks
import dreamcoder.domains.clevr.test_makeClevrTasks as test_makeClevrTasks
import dreamcoder.domains.clevr.test_clevrPrimitives as test_clevrPrimitives
import dreamcoder.domains.clevr.test_clevrPrimitivesOcaml as test_clevrPrimitivesOcaml
import dreamcoder.domains.clevr.test_clevrRecognition as test_clevrRecognition
import dreamcoder.domains.clevr.test_clevrIntegration as test_clevrIntegration

import os
import random

"""
main.py (CLEVR) | Author: Catherine Wong
This is the main file for the CLEVR-based symbolic scene reasoning domain. It contains the domain-specific feature extractor and launch arguments for the CLEVR domain (though it is usually launched via the bin/clevr.py convenience file).

This dataset requires data generated by the Extended CLEVR dataset (https://github.com/CatherineWong/too_clevr). 

Example usage: python bin/clevr.py
                --taskDatasets all
                --primitives clevr_bootstrap clevr_map_transform
Example tests:
    --run_makeClevrTasks_test # Making and loading CLEVR tasks.
    --run_clevrPrimitivesPython_test # CLEVR primitives in Python.
    --run_clevrPrimitivesOcaml_test # CLEVR primitives in OCaml
"""
# Dictionary of domain-specific arguments constructed in this file, which need to be passed to the main iterator.
DOMAIN_SPECIFIC_ARGS = {
    "grammar" : None,
    "tasks" : None, # Training tasks.
    "testingTasks" : None,
    "outputPrefix": None, # Output prefix for the checkpoint files,
}
DEFAULT_CLEVR_EVALUATION_TIMEOUT = 0.5
DEFAULT_CLEVR_DOMAIN_NAME_PREFIX = "clevr"
DEFAULT_TASK_DATASET_DIR = f"data/{DEFAULT_CLEVR_DOMAIN_NAME_PREFIX}"
DEFAULT_LANGUAGE_DIR = f"data/{DEFAULT_CLEVR_DOMAIN_NAME_PREFIX}/language/"

def clevr_options(parser):
    ### Dataset loading options.
    parser.add_argument("--curriculumDatasets", type=str, nargs="*",
                        default=[],
                        help="A list of curriculum datasets, stored as JSON CLEVR question files. These will be run through separately.")
    parser.add_argument("--taskDatasets", type=str, nargs="*",
                        default=["all"],
                        help="Which task datasets to load, stored as JSON CLEVR question files, or 'all' to load all of the datasets in the directory.")
    parser.add_argument("--taskDatasetDir",
                        default=DEFAULT_TASK_DATASET_DIR,
                        help="Top level directory for the dataset.")
    parser.add_argument("--languageDatasetDir",
                        default=DEFAULT_LANGUAGE_DIR)
    parser.add_argument("--topLevelOutputDirectory",
                        default=DEFAULT_OUTPUT_DIRECTORY, # Defined in utilities.py
                        help="Top level directory in which to store outputs. By default, this is the experimentOutputs directory.")
                        
    # Experiment iteration parameters.
    parser.add_argument("--primitives",
                        nargs="*",
                        default=["clevr_bootstrap", "clevr_map_transform"],
                        help="Which primitives to use. Choose from: [clevr_original, clevr_bootstrap, clevr_map_transform, clevr_filter, clevr_filter_except, clevr_difference]")
    parser.add_argument("--evaluationTimeout",
                        default=DEFAULT_CLEVR_EVALUATION_TIMEOUT,
                        help="How long to spend evaluating a given CLEVR tasks.")
    parser.add_argument("--iterations_as_epochs",
                        default=True,
                        help="Whether to take the iterations value as an epochs value.")
    
    
    # Entrypoint functionalities. We overload this file as an entrypoint for certain other functionalities and analyses.
    parser.add_argument("--generate_ocaml_definitions",
                        action='store_true',
                        help="Entrypoint functionality to generate OCaml definitions from the current primitive set.")
                        
    # Test functionalities.
    parser.add_argument("--run_makeClevrTasks_test",
                        action='store_true',
                        help='Runs tests for makeClevrTasks.py, which controls loading the CLEVR task datasets.')
    parser.add_argument("--run_clevrPrimitivesPython_test",
                        action='store_true',
                        help='Runs tests for clevrPrimitives.py, which controls the Python implementations of the CLEVR DSL primitives.')
    parser.add_argument("--run_clevrPrimitivesOcaml_test",
                        action='store_true',
                        help='Runs tests for clevrSolver.ml, which controls the OCaml implementations of the CLEVR DSL primitives.')
    parser.add_argument("--run_clevrRecognition_test",
                        action='store_true',
                        help='Runs tests for clevrRecognition.py, which controls the .')
    parser.add_argument("--run_clevrIntegration_test",
                        action='store_true')

def run_unit_tests(args):
    if args.pop("run_makeClevrTasks_test"):
        test_makeClevrTasks.test_all()
        exit(0)
    if args.pop("run_clevrPrimitivesPython_test"):
        test_clevrPrimitives.test_all()
        exit(0)
    if args.pop("run_clevrPrimitivesOcaml_test"):
        test_clevrPrimitivesOcaml.test_all()
        exit(0)
    if args.pop("run_clevrRecognition_test"):
        test_clevrRecognition.test_all()
        exit(0)
def run_entrypoint_functionalities(args):
    # Runs any other analyses that require the main file as an entrypoint.
    if args.pop("generate_ocaml_definitions"):
        generate_ocaml_definitions()
        
def run_integration_test(DOMAIN_SPECIFIC_ARGS, args):
    if args.pop("run_clevrIntegration_test"):
        test_clevrIntegration.test_all(DOMAIN_SPECIFIC_ARGS, args)
        exit(0)
                
def main(args):
    # Entrypoint for running any unit tests.
    run_unit_tests(args)
    
    train_tasks, test_tasks, language_dataset = makeClevrTasks.loadAllTaskAndLanguageDatasets(args)
    
    # Load the primitives and optionally run tests with the primitive set.
    primitive_names = args.pop("primitives")
    primitives = load_clevr_primitives(primitive_names)
    initial_grammar = Grammar.uniform(primitives)
    print("Using starting grammar")
    print(initial_grammar)
    
    # Get the evaluation timeout for each task, and the iterations we should run as a whole.
    evaluation_timeout = args.pop("evaluationTimeout")
    eprint(f"Now running with an evaluation timeout of [{evaluation_timeout}].")
    convert_iterations_to_training_task_epochs(args, train_tasks)
    
    # Create a directory 
    top_level_output_dir = args.pop("topLevelOutputDirectory")
    checkpoint_output_prefix = get_timestamped_output_directory_for_checkpoints(top_level_output_dir=top_level_output_dir, domain_name=DEFAULT_CLEVR_DOMAIN_NAME_PREFIX)
    
    
    # Set all of the domain specific arguments.
    args["languageDataset"] = language_dataset
    DOMAIN_SPECIFIC_ARGS["tasks"] = train_tasks
    DOMAIN_SPECIFIC_ARGS["testingTasks"] = test_tasks
    DOMAIN_SPECIFIC_ARGS["grammar"] = initial_grammar
    DOMAIN_SPECIFIC_ARGS["outputPrefix"] = checkpoint_output_prefix
    DOMAIN_SPECIFIC_ARGS['evaluationTimeout'] = evaluation_timeout
    
    # Run the integration test immediately before we remove all domain-specific arguments
    # and run the iterator itself.
    run_integration_test(DOMAIN_SPECIFIC_ARGS, args)
    
    # Utility to pop off any additional arguments that are specific to this domain.
    pop_all_domain_specific_args(args_dict=args, iterator_fn=ecIterator)
    generator = ecIterator(**DOMAIN_SPECIFIC_ARGS,
                           **args)
    for result in generator:
        pass
        